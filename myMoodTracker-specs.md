# Specifications — myMoodTracker (daily tracking app: mood, dreams, goals, tasks)

## 1. Overview

Local web app (LAN only), usable on mobile and desktop via browser. Two users identified by a simple profile selection confirmed with a password.

**Chosen stack:**
- Backend: **FastAPI** (Python)
- Frontend: **HTMX** + CSS (lightweight, no JS build step, server-side rendering — consistent with "simple internal use")
- Database: **SQLite** (single file, trivial backup)
- PDF export: **WeasyPrint** (HTML → PDF rendering, consistent with a Python/Jinja2 stack, no extra client-side dependency)
- Local network access: Uvicorn bound on `0.0.0.0`, accessible via `http://<local-ip>:<port>` from any device on the LAN
- Internationalization: FR/EN translation dictionaries loaded into Jinja2 templates based on the logged-in profile's language preference (no need for a heavy i18n framework given the limited number of text strings)

## 2. Users

- 2 fixed profiles, created on first launch (name + associated color to visually distinguish their entries)
- Each profile has a **simple password** (privacy protection between the two people, not hardened security — hash stored in the database, e.g. bcrypt via `passlib`, no complex session management like JWT/OAuth given the trusted LAN context)
- After login, a lightweight server-side session cookie (just to avoid re-entering the password on every page)
- **Per-entry visibility**: each personal data item (mood, dream, goal, event) is created with a **private** status (visible only to its author) or **public** status (also visible to the other profile), chosen by the user at entry time. Default: private.
- The task list is **always shared** (no visibility concept applies to it, as it's inherently common)
- **Interface language**: choice between French and English in settings, per profile (individual preference — each person can have their own language)

## 3. Detailed features

### 3.1 Daily mood
One entry per user per day (editable during the day). Suggested indicators, each on a 1–10 scale with a slider:
- Physical fatigue
- Mental fatigue
- Morale / overall mood
- Need for social interaction
- Stress level
- Sleep quality (previous night)

Optional free-text field (short note) to add context to the day.

### 3.2 Dream journal
- Optional entry per day (can be left empty)
- Free text
- Optional tag: "pleasant / neutral / nightmare" (makes later review easier)

### 3.3 Daily goals
- List of 1 to N goals entered in the morning (or at any time)
- Each goal has a checkbox
- Retrospective view: completion rate per day/week (simple calculation, no complex dashboard in V1)

### 3.4 Shared task list
- Tasks visible to both profiles
- Fields: label, status (to do / done), assigned to (optional, either user or "both"), creation date
- Any change is immediately visible to the other user (simple refresh on page load, no websocket in V1 — consistent with the intended simplicity)

### 3.5 Notable events / emotions
- Ability to add, at any time during the day, one or more one-off events with their emotional charge: **positive** or **negative**
- Multiple entries possible on the same day (unlike mood, which is a single daily entry)
- Useful for later linking a mood dip/rise to a specific event when reviewing history

**Positive event** — simple entry: short description, approximate time (optional).

**Negative event** — full functional analysis grid (CBT-style approach), to better understand what happened:
- Trigger (what preceded/caused the situation)
- Aggravating factors (context that amplified the reaction: fatigue, pre-existing stress, etc.)
- First signs (early cues before the emotion escalated)
- Emotion felt + intensity (0 to 10)
- Thoughts fueling the emotion
- Physiological reactions (tension, increased heart rate, etc.)
- Behavior adopted
- Consequences (on oneself, on the relationship, on the rest of the day)

**"Core need" tag (optional, on both events AND daily mood, multi-select)**: each entry can be linked to **one or more** needs from a fixed reference list, organized by category (Security, Competence, Self-expression, Limits, Spontaneity — each with its own specific needs, e.g. stability, comfort, belonging, autonomy, achievement, empathy, structure, creativity, etc.). A complex situation can involve several needs at once (e.g. "respect" + "security"). Goal: identify over time which needs recur as met or unmet around mood variations.

### 3.6 PDF export (for psychological follow-up)
- Export of negative events over a given period, in table format — one row per event, columns: Date/time, Trigger, Aggravating factors, First signs, Emotion, Intensity (0-10), Thoughts, Physiological reactions, Behavior, Consequences (format deliberately kept close to the original grid, without a core-needs column)
- Date range selection before export (e.g. "last month", or custom dates)
- The generated PDF file is downloadable directly from the browser, for personal tracking or to share with a professional
- Server-side generation: data flows through an HTML template (Jinja2, consistent with the rest of the HTMX stack) converted to PDF via **WeasyPrint**, avoiding an extra client-side JS dependency

### 3.7 History / review
- Calendar or chronological list view to look back at previous days (mood + dreams + goals for the chosen day)
- Filter by user
- Positive/negative events for the day are displayed alongside mood to make the connection easier

## 4. Data model (SQLite)

```sql
users (
  id INTEGER PRIMARY KEY,
  name TEXT,
  color TEXT,
  password_hash TEXT,
  language TEXT DEFAULT 'fr'    -- 'fr' or 'en', per-profile interface preference
)

mood_entries (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  date DATE,
  physical_fatigue INTEGER,    -- 1-10
  mental_fatigue INTEGER,      -- 1-10
  mood INTEGER,                -- 1-10
  social_need INTEGER,         -- 1-10
  stress INTEGER,              -- 1-10
  sleep_quality INTEGER,       -- 1-10
  note TEXT,
  visibility TEXT DEFAULT 'private',   -- private / public
  UNIQUE(user_id, date)
)

dreams (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  date DATE,
  content TEXT,
  tag TEXT,                    -- pleasant / neutral / nightmare
  visibility TEXT DEFAULT 'private'
)

events (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  date DATE,
  time TEXT NULL,               -- approximate time, optional
  type TEXT,                    -- positive / negative
  description TEXT,             -- short summary (required if positive, optional if negative)
  visibility TEXT DEFAULT 'private',
  -- fields filled only if type = negative (functional analysis grid)
  trigger TEXT NULL,
  aggravating_factors TEXT NULL,
  first_signs TEXT NULL,
  emotion TEXT NULL,
  intensity INTEGER NULL,       -- 0-10
  thoughts TEXT NULL,
  physiological_reactions TEXT NULL,
  behavior TEXT NULL,
  consequences TEXT NULL
)

needs (
  id INTEGER PRIMARY KEY,
  category TEXT,                -- Security / Competence / Self-expression / Limits / Spontaneity
  name TEXT                     -- Stability, Comfort, Belonging, Autonomy, Achievement, etc.
)
-- reference table pre-filled once on first launch (fixed list of ~28 needs)

entry_needs (
  id INTEGER PRIMARY KEY,
  entry_type TEXT,              -- 'event' or 'mood'
  entry_id INTEGER,             -- id of the related events or mood_entries row
  need_id INTEGER               -- reference to needs.id
)

daily_goals (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  date DATE,
  label TEXT,
  done BOOLEAN DEFAULT 0,
  visibility TEXT DEFAULT 'private'
)

shared_tasks (
  id INTEGER PRIMARY KEY,
  label TEXT,
  status TEXT DEFAULT 'todo',   -- todo / done
  assigned_to INTEGER NULL,     -- user_id or NULL (both)
  created_at DATETIME
)
```

## 5. API endpoints (FastAPI)

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Login screen (profile selection + password) |
| POST | `/login` | Verifies the password, opens the session |
| POST | `/logout` | Closes the session |
| GET | `/dashboard` | Today's home screen (user inferred from session) |
| POST | `/mood` | Create/update today's mood entry (with `visibility`, optional `needs[]`) |
| POST | `/dreams` | Add a dream (with `visibility`) |
| POST | `/events` | Add an event — fields vary by `type` (simple if positive, full grid if negative), `visibility`, optional `needs[]` |
| GET | `/events?date=` | List my events + the other profile's public ones, for a given day |
| GET | `/needs` | List the reference list of core needs, grouped by category |
| POST | `/goals` | Add a goal (with `visibility`) |
| PATCH | `/goals/{id}` | Check/uncheck a goal |
| PATCH | `/{table}/{id}/visibility` | Toggle an entry private ↔ public |
| GET | `/tasks` | List shared tasks (always visible to both) |
| POST | `/tasks` | Create a task |
| PATCH | `/tasks/{id}` | Update status/assignment |
| GET | `/history?date=` | Review a past day: my data + partner's public data |
| GET | `/export/pdf?date_from=&date_to=` | Generates and downloads the negative-events tracking PDF for the chosen period |
| PATCH | `/settings/language` | Changes the logged-in profile's interface language (`fr` / `en`) |

Each HTMX route returns an HTML fragment (no client-side JSON), staying in the spirit of "no front-end build step." Visibility is enforced server-side: any request filtering another `user_id`'s data automatically excludes rows with `visibility = 'private'`.

## 6. Interface (pages)

1. **Login** — profile choice + password field
2. **Today's dashboard** — mood sliders (+ optional needs tag), dream field, today's goal list with checkboxes, an "add event" block with two distinct forms: quick entry for a positive event, full analysis grid (trigger → consequences) for a negative event, each with an optional needs tag and a 🔒 private / 🌐 public toggle
3. **Shared tasks** — common list, quick add, filter by assignee (no visibility concept here)
4. **History** — date picker, read-only display of my data for the chosen day + the partner's public data for that same day, with a PDF export button (date range selection) for negative events
5. **Settings** — language selector (French / English), specific to each profile

Mobile responsive: single-column layout, sliders and buttons sized for touch (≥ 44px target).

## 7. Local network deployment

- Launch: `uvicorn app:app --host 0.0.0.0 --port 8000`
- Access from mobile/another PC on the LAN via the host machine's local IP (e.g. `192.168.1.x:8000`)
- No HTTPS needed for closed LAN use (to be documented as a limitation if the network isn't trusted)
- Backup: copying the SQLite `.db` file is enough

**Chosen hosting:** dedicated Raspberry Pi 4 (4 GB RAM), micro-SD card (A1/A2 class recommended for durability given frequent SQLite + monitoring writes), plugged in continuously on the local network. This machine also hosts other lightweight services planned by the user (file sharing, monitoring) alongside this app. The Freebox mini 4K stays unchanged, acting only as router/DHCP. Regular backup of the `.db` file is recommended given the write load on the SD card.

*Alternative considered:* switching to a Freebox Pop or Ultra to host the app in an ARM64 Linux VM via Freebox OS — ruled out as it implies a recurring cost (~+5 to +25 €/month compared to the current 35 €/month subscription once the promo period ends) for a need a Raspberry Pi covers with a single one-time expense (40-90 €).

## 8. MVP vs V2 scope

**MVP (V1)**
- Password login, mood/dream/daily-goal entry, positive/negative events (with private/public visibility), shared tasks, simple list history, PDF export of negative events

**V2 (ideas)**
- Trend charts (fatigue/mood evolution over 30 days)
- Daily reminder/notification
- CSV data export
- Websocket for real-time sync of shared tasks
