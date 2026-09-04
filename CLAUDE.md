# CLAUDE.md — myMoodTracker

Guidance for Claude Code (or any contributor) working in this repository.
Full functional/technical spec: `myMoodTracker-specs.md` (read it before making structural changes — this file only covers coding conventions and workflow).

## Stack

- **Backend:** FastAPI (Python 3.11+)
- **Frontend:** HTMX + Jinja2 templates + plain CSS — no JS framework, no build step
- **DB:** SQLite, accessed via `sqlite3` (stdlib) or `aiosqlite` if async access is needed — no ORM unless a real need appears (keep it light)
- **PDF export:** WeasyPrint, fed by a Jinja2 HTML template
- **Server:** Uvicorn, bound to `0.0.0.0`, deployed on a Raspberry Pi 4 on the local network

## Project structure (target)

```
app/
  main.py                # FastAPI app, route registration
  db.py                  # connection helper, schema init, migrations
  auth.py                # password hashing, session handling
  routers/
    mood.py
    dreams.py
    events.py
    goals.py
    tasks.py
    history.py
    export.py
    settings.py
  templates/
    base.html
    dashboard.html
    history.html
    settings.html
    partials/            # HTMX fragments returned by POST/PATCH endpoints
      mood_card.html
      event_row.html
      goal_item.html
      task_row.html
  static/
    style.css
  i18n/
    fr.json
    en.json
  pdf/
    negative_events_template.html
db/
  mymoodtracker.db        # not committed — see .gitignore
tests/
  test_mood.py
  test_events.py
  test_auth.py
  ...
CLAUDE.md
myMoodTracker-specs.md
requirements.txt
```

## Coding conventions

- **Python style:** PEP 8, type hints on all function signatures, docstrings on public functions/route handlers (one line is enough for simple ones).
- **Route handlers stay thin.** Business logic (queries, validation beyond Pydantic, computing streaks/completion rates) lives in small helper functions, not inline in the route body — makes handlers easy to test and read.
- **Pydantic models** for request bodies (e.g. `MoodEntryIn`, `EventIn`). Let FastAPI handle validation errors; don't hand-roll input checks that Pydantic already covers.
- **SQL:** parametrized queries only (`?` placeholders) — never string-interpolate user input into SQL, even though this is a trusted LAN app.
- **Naming:** snake_case for Python, kebab-case for template filenames, and match the English column names from the data model in `myMoodTracker-specs.md` exactly (e.g. `physical_fatigue`, not `fatigue_physique`) — the spec is the source of truth for schema naming.
- **No dead config toggles.** If a feature is V2 (per the specs' MVP/V2 split), don't scaffold it "just in case" — add it when it's actually being built.

## HTMX / templates conventions

- Every route that's called via `hx-post` / `hx-patch` / `hx-get` returns a **fragment template** from `templates/partials/`, never a full page and never raw JSON.
- Full-page routes (`GET /dashboard`, `GET /history`, ...) render a template that extends `base.html`.
- Keep `hx-target` / `hx-swap` attributes in the calling template close to the element they affect — don't scatter HTMX wiring across multiple files for one interaction.
- Visibility filtering (private/public) happens in the query layer (`db.py` helpers), not in the template — a template should never receive private data it then has to hide.

## i18n

- All user-facing strings go through the translation dict (`i18n/fr.json` / `i18n/en.json`), keyed by short identifiers (e.g. `"mood.stress_label"`), not full sentences as keys.
- The active language comes from the logged-in profile's `users.language` column and is injected into the Jinja2 context once per request (a small dependency/middleware, not per-route boilerplate).
- New strings: add the key to **both** JSON files in the same commit — never leave one language behind.

## Auth & sessions

- Passwords hashed with `passlib` (bcrypt). Never log or print a password or its hash.
- Session = a signed server-side cookie (e.g. `itsdangerous` or FastAPI's `SessionMiddleware`), not a JWT — no need for that complexity on a two-user LAN app.
- Every route that touches personal data must resolve the current user from the session, never from a client-supplied `user_id` query/body param — that would let one profile impersonate the other.

## Tests

- `pytest`, with FastAPI's `TestClient`.
- One test module per router (`tests/test_mood.py` etc.), covering: happy path, visibility filtering (private entry not visible to the other user), and the negative-event grid's required-vs-optional fields.
- Use a temporary SQLite file (or `:memory:`) per test run — never point tests at the real `db/mymoodtracker.db`.

## Running locally

```
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Deployment (Raspberry Pi)

- Same `uvicorn` command, without `--reload`, ideally behind a `systemd` service so it restarts on boot/crash.
- Back up `db/mymoodtracker.db` regularly (SD card write wear — see specs §7).

## Things to avoid

- No client-side state management (React/Vue/vanilla JS beyond what HTMX needs) — if a feature seems to need it, that's a signal to re-check the spec rather than reach for a framework.
- No `localStorage`/`sessionStorage` reliance for anything that must survive across devices — this is a multi-device LAN app, state belongs in SQLite.
- No adding authentication complexity (OAuth, JWT, 2FA) beyond what's in the spec — this is explicitly a low-friction two-person household app, not a public-facing product.