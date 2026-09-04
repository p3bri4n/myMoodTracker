"""Connexion SQLite, initialisation du schéma, et accès aux données.

Toute la logique de filtrage de visibilité (privé/public) vit ici, jamais
dans les templates ni les routes, conformément à CLAUDE.md.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Generator
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime

# (catégorie, nom) — table de référence des "besoins fondamentaux", fixe.
NEEDS_SEED: list[tuple[str, str]] = [
    ("Security", "stability"),
    ("Security", "safety"),
    ("Security", "comfort"),
    ("Security", "belonging"),
    ("Security", "trust"),
    ("Security", "empathy"),
    ("Competence", "achievement"),
    ("Competence", "competence"),
    ("Competence", "growth"),
    ("Competence", "recognition"),
    ("Competence", "effectiveness"),
    ("Self-expression", "creativity"),
    ("Self-expression", "authenticity"),
    ("Self-expression", "self_expression"),
    ("Self-expression", "meaning"),
    ("Self-expression", "humor"),
    ("Limits", "autonomy"),
    ("Limits", "structure"),
    ("Limits", "respect"),
    ("Limits", "boundaries"),
    ("Limits", "fairness"),
    ("Limits", "order"),
    ("Spontaneity", "playfulness"),
    ("Spontaneity", "novelty"),
    ("Spontaneity", "freedom"),
    ("Spontaneity", "spontaneity"),
    ("Spontaneity", "adventure"),
    ("Spontaneity", "curiosity"),
]

# Roue des émotions (style Plutchik) : core -> secondary -> [specific, ...].
# Table de référence fixe, seedée une fois (144 lignes = 6 x 4 x 6).
EMOTIONS_WHEEL: dict[str, dict[str, list[str]]] = {
    "Anger": {
        "Critical": ["Sarcastic", "Sceptical", "Suspicious", "Judgmental", "Withdrawn", "Disrespected"],
        "Resentful": ["Betrayed", "Indignant", "Violated", "Aggrieved", "Bitter", "Let down"],
        "Hostile": ["Hateful", "Vengeful", "Provoked", "Threatened", "Seething", "Infuriated"],
        "Irritated": ["Agitated", "Frustrated", "Annoyed", "Impatient", "Aggravated", "On edge"],
    },
    "Disgust": {
        "Judgmental": ["Disgusted", "Revolted", "Contemptuous", "Disapproving", "Appalled", "Repelled"],
        "Disappointed": ["Disillusioned", "Dismayed", "Displeased", "Let down", "Disenchanted", "Discouraged"],
        "Awful": ["Nauseated", "Detestable", "Loathsome", "Repugnant", "Repulsed", "Sickened"],
        "Avoidant": ["Averse", "Reluctant", "Withdrawn", "Distant", "Guarded", "Hesitant"],
    },
    "Sadness": {
        "Guilty": ["Ashamed", "At fault", "Remorseful", "Culpable", "Regretful", "Embarrassed"],
        "Lonely": ["Isolated", "Abandoned", "Forsaken", "Rejected", "Excluded", "Distant"],
        "Despairing": ["Hopeless", "Grief-stricken", "Powerless", "Empty", "Discouraged", "Helpless"],
        "Vulnerable": ["Fragile", "Victimized", "Hurt", "Wounded", "Insecure", "Exposed"],
    },
    "Fear": {
        "Insecure": ["Anxious", "Threatened", "Nervous", "Overwhelmed", "Worried", "Inadequate"],
        "Scared": ["Terrified", "Panicked", "Frightened", "Alarmed", "Petrified", "Startled"],
        "Rejected": ["Excluded", "Persecuted", "Alienated", "Disrespected", "Ridiculed", "Humiliated"],
        "Confused": ["Doubtful", "Bewildered", "Perplexed", "Hesitant", "Torn", "Uncertain"],
    },
    "Surprise": {
        "Confused": ["Startled", "Stunned", "Disillusioned", "Perplexed", "Astonished", "Dazed"],
        "Amazed": ["Awed", "Astounded", "Wonderstruck", "Speechless", "Overwhelmed", "Dumbfounded"],
        "Excited": ["Eager", "Energetic", "Enthusiastic", "Lively", "Animated", "Elated"],
        "Uncertain": ["Puzzled", "Disoriented", "Shocked", "Unsettled", "Baffled", "Wary"],
    },
    "Joy": {
        "Interested": ["Curious", "Inspired", "Engaged", "Fascinated", "Absorbed", "Intrigued"],
        "Content": ["Peaceful", "Satisfied", "Grateful", "Fulfilled", "Serene", "Relaxed"],
        "Proud": ["Confident", "Successful", "Accomplished", "Valued", "Respected", "Triumphant"],
        "Optimistic": ["Hopeful", "Encouraged", "Energized", "Uplifted", "Eager", "Cheerful"],
    },
}

EMOTIONS_SEED: list[tuple[str, str, str]] = [
    (core, secondary, specific)
    for core, secondaries in EMOTIONS_WHEEL.items()
    for secondary, specifics in secondaries.items()
    for specific in specifics
]

# Tables sur lesquelles la bascule privé/public générique est autorisée.
VISIBILITY_TABLES = {"mood_entries", "dreams", "events", "daily_goals"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  color TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  language TEXT DEFAULT 'fr'
);

CREATE TABLE IF NOT EXISTS mood_entries (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  date DATE NOT NULL,
  physical_fatigue INTEGER,
  mental_fatigue INTEGER,
  mood INTEGER,
  social_need INTEGER,
  stress INTEGER,
  sleep_quality INTEGER,
  note TEXT,
  visibility TEXT DEFAULT 'private',
  UNIQUE(user_id, date)
);

CREATE TABLE IF NOT EXISTS dreams (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  date DATE NOT NULL,
  content TEXT,
  tag TEXT,
  visibility TEXT DEFAULT 'private'
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  date DATE NOT NULL,
  time TEXT,
  type TEXT NOT NULL,
  description TEXT,
  visibility TEXT DEFAULT 'private',
  trigger TEXT,
  aggravating_factors TEXT,
  first_signs TEXT,
  intensity INTEGER,
  thoughts TEXT,
  physiological_reactions TEXT,
  behavior TEXT,
  consequences TEXT,
  caused_by_event_id INTEGER REFERENCES events(id),
  emotion_id INTEGER REFERENCES emotions(id)
);

CREATE TABLE IF NOT EXISTS needs (
  id INTEGER PRIMARY KEY,
  category TEXT NOT NULL,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entry_needs (
  id INTEGER PRIMARY KEY,
  entry_type TEXT NOT NULL,
  entry_id INTEGER NOT NULL,
  need_id INTEGER NOT NULL REFERENCES needs(id)
);

CREATE TABLE IF NOT EXISTS emotions (
  id INTEGER PRIMARY KEY,
  core TEXT NOT NULL,
  secondary TEXT NOT NULL,
  specific TEXT NOT NULL,
  UNIQUE(core, secondary, specific)
);

CREATE TABLE IF NOT EXISTS daily_goals (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  date DATE NOT NULL,
  label TEXT NOT NULL,
  done BOOLEAN DEFAULT 0,
  visibility TEXT DEFAULT 'private'
);

CREATE TABLE IF NOT EXISTS shared_tasks (
  id INTEGER PRIMARY KEY,
  label TEXT NOT NULL,
  status TEXT DEFAULT 'todo',
  assigned_to INTEGER REFERENCES users(id),
  created_at DATETIME
);
"""


@dataclass
class User:
    id: int
    name: str
    color: str
    password_hash: str
    language: str


def get_db_path() -> str:
    """Retourne le chemin du fichier SQLite (surchargeable pour les tests)."""
    return os.environ.get("MYMOODTRACKER_DB_PATH", "db/mymoodtracker.db")


def connect(db_path: str | None = None) -> sqlite3.Connection:
    """Ouvre une connexion SQLite avec row_factory et clés étrangères actives."""
    conn = sqlite3.connect(db_path or get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(
        row["name"] == column for row in conn.execute(f"PRAGMA table_info({table})")
    )


# Colonnes ajoutées après la création initiale des tables : (table, colonne, DDL du ALTER).
# CREATE TABLE IF NOT EXISTS ne modifie pas un schéma existant, donc toute colonne
# ajoutée au SCHEMA ci-dessus doit aussi être listée ici pour les bases déjà créées.
_COLUMN_MIGRATIONS = [
    ("events", "caused_by_event_id", "ALTER TABLE events ADD COLUMN caused_by_event_id INTEGER REFERENCES events(id)"),
    ("events", "emotion_id", "ALTER TABLE events ADD COLUMN emotion_id INTEGER REFERENCES emotions(id)"),
]


def init_db(conn: sqlite3.Connection) -> None:
    """Crée les tables si besoin, applique les migrations de colonnes, et seed `needs`/`emotions`."""
    conn.executescript(SCHEMA)
    for table, column, ddl in _COLUMN_MIGRATIONS:
        if not _column_exists(conn, table, column):
            conn.execute(ddl)
    row = conn.execute("SELECT COUNT(*) AS n FROM needs").fetchone()
    if row["n"] == 0:
        conn.executemany(
            "INSERT INTO needs (category, name) VALUES (?, ?)", NEEDS_SEED
        )
    row = conn.execute("SELECT COUNT(*) AS n FROM emotions").fetchone()
    if row["n"] == 0:
        conn.executemany(
            "INSERT INTO emotions (core, secondary, specific) VALUES (?, ?, ?)", EMOTIONS_SEED
        )
    conn.commit()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Dépendance FastAPI : une connexion par requête."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


# --- Users -----------------------------------------------------------------


def count_users(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]


def create_user(
    conn: sqlite3.Connection, name: str, color: str, password_hash: str
) -> int:
    cur = conn.execute(
        "INSERT INTO users (name, color, password_hash, language) VALUES (?, ?, ?, 'fr')",
        (name, color, password_hash),
    )
    conn.commit()
    return cur.lastrowid


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> User | None:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return User(**dict(row)) if row else None


def list_users(conn: sqlite3.Connection) -> list[User]:
    rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    return [User(**dict(r)) for r in rows]


def list_users_by_id(conn: sqlite3.Connection) -> dict[int, User]:
    return {u.id: u for u in list_users(conn)}


def set_user_language(conn: sqlite3.Connection, user_id: int, language: str) -> None:
    conn.execute("UPDATE users SET language = ? WHERE id = ?", (language, user_id))
    conn.commit()


# --- Visibility filtering (shared by mood/dreams/events/goals) -------------


def list_visible_for_date(
    conn: sqlite3.Connection, table: str, date: date_type | str, requesting_user_id: int
) -> list[sqlite3.Row]:
    """Mes entrées du jour + les entrées publiques de l'autre profil."""
    assert table in VISIBILITY_TABLES
    query = (
        f"SELECT * FROM {table} "
        "WHERE date = ? AND (user_id = ? OR visibility = 'public') "
        "ORDER BY id"
    )
    return conn.execute(query, (str(date), requesting_user_id)).fetchall()


def toggle_visibility(
    conn: sqlite3.Connection, table: str, entry_id: int, user_id: int
) -> sqlite3.Row | None:
    """Bascule privé <-> public pour une entrée dont l'appelant est propriétaire."""
    if table not in VISIBILITY_TABLES:
        return None
    row = conn.execute(
        f"SELECT * FROM {table} WHERE id = ? AND user_id = ?", (entry_id, user_id)
    ).fetchone()
    if row is None:
        return None
    new_visibility = "public" if row["visibility"] == "private" else "private"
    conn.execute(
        f"UPDATE {table} SET visibility = ? WHERE id = ?", (new_visibility, entry_id)
    )
    conn.commit()
    return conn.execute(f"SELECT * FROM {table} WHERE id = ?", (entry_id,)).fetchone()


# --- Needs -------------------------------------------------------------------


def get_needs_grouped(conn: sqlite3.Connection) -> dict[str, list[sqlite3.Row]]:
    rows = conn.execute("SELECT * FROM needs ORDER BY category, name").fetchall()
    grouped: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(row["category"], []).append(row)
    return grouped


def attach_needs(
    conn: sqlite3.Connection, entry_type: str, entry_id: int, need_ids: list[int]
) -> None:
    conn.executemany(
        "INSERT INTO entry_needs (entry_type, entry_id, need_id) VALUES (?, ?, ?)",
        [(entry_type, entry_id, need_id) for need_id in need_ids],
    )
    conn.commit()


def replace_needs(
    conn: sqlite3.Connection, entry_type: str, entry_id: int, need_ids: list[int]
) -> None:
    conn.execute(
        "DELETE FROM entry_needs WHERE entry_type = ? AND entry_id = ?",
        (entry_type, entry_id),
    )
    if need_ids:
        attach_needs(conn, entry_type, entry_id, need_ids)
    else:
        conn.commit()


def get_needs_for_entry(
    conn: sqlite3.Connection, entry_type: str, entry_id: int
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT needs.* FROM needs "
        "JOIN entry_needs ON entry_needs.need_id = needs.id "
        "WHERE entry_needs.entry_type = ? AND entry_needs.entry_id = ? "
        "ORDER BY needs.category, needs.name",
        (entry_type, entry_id),
    ).fetchall()


# --- Mood --------------------------------------------------------------------


def upsert_mood_entry(
    conn: sqlite3.Connection,
    user_id: int,
    date: date_type | str,
    physical_fatigue: int,
    mental_fatigue: int,
    mood: int,
    social_need: int,
    stress: int,
    sleep_quality: int,
    note: str | None,
    visibility: str,
) -> sqlite3.Row:
    conn.execute(
        """
        INSERT INTO mood_entries
            (user_id, date, physical_fatigue, mental_fatigue, mood, social_need,
             stress, sleep_quality, note, visibility)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, date) DO UPDATE SET
            physical_fatigue = excluded.physical_fatigue,
            mental_fatigue = excluded.mental_fatigue,
            mood = excluded.mood,
            social_need = excluded.social_need,
            stress = excluded.stress,
            sleep_quality = excluded.sleep_quality,
            note = excluded.note,
            visibility = excluded.visibility
        """,
        (
            user_id,
            str(date),
            physical_fatigue,
            mental_fatigue,
            mood,
            social_need,
            stress,
            sleep_quality,
            note,
            visibility,
        ),
    )
    conn.commit()
    return conn.execute(
        "SELECT * FROM mood_entries WHERE user_id = ? AND date = ?",
        (user_id, str(date)),
    ).fetchone()


def get_mood_entry(
    conn: sqlite3.Connection, user_id: int, date: date_type | str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM mood_entries WHERE user_id = ? AND date = ?",
        (user_id, str(date)),
    ).fetchone()


# --- Dreams -------------------------------------------------------------------


def create_dream(
    conn: sqlite3.Connection,
    user_id: int,
    date: date_type | str,
    content: str,
    tag: str | None,
    visibility: str,
) -> sqlite3.Row:
    cur = conn.execute(
        "INSERT INTO dreams (user_id, date, content, tag, visibility) VALUES (?, ?, ?, ?, ?)",
        (user_id, str(date), content, tag, visibility),
    )
    conn.commit()
    return conn.execute(
        "SELECT * FROM dreams WHERE id = ?", (cur.lastrowid,)
    ).fetchone()


# --- Emotions (3-level wheel: core -> secondary -> specific) -----------------


def list_emotion_cores(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT DISTINCT core FROM emotions ORDER BY core").fetchall()
    return [r["core"] for r in rows]


def list_emotion_secondaries(conn: sqlite3.Connection, core: str) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT secondary FROM emotions WHERE core = ? ORDER BY secondary",
        (core,),
    ).fetchall()
    return [r["secondary"] for r in rows]


def list_emotion_specifics(
    conn: sqlite3.Connection, core: str, secondary: str
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM emotions WHERE core = ? AND secondary = ? ORDER BY specific",
        (core, secondary),
    ).fetchall()


def get_emotion_by_id(conn: sqlite3.Connection, emotion_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM emotions WHERE id = ?", (emotion_id,)).fetchone()


# --- Events -------------------------------------------------------------------


def create_event(conn: sqlite3.Connection, **fields) -> sqlite3.Row:
    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO events ({columns}) VALUES ({placeholders})",
        tuple(fields.values()),
    )
    conn.commit()
    return conn.execute("SELECT * FROM events WHERE id = ?", (cur.lastrowid,)).fetchone()


def list_negative_events_for_period(
    conn: sqlite3.Connection, user_id: int, date_from: str, date_to: str
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT events.*, "
        "emotions.core AS emotion_core, emotions.secondary AS emotion_secondary, "
        "emotions.specific AS emotion_specific "
        "FROM events LEFT JOIN emotions ON emotions.id = events.emotion_id "
        "WHERE events.user_id = ? AND events.type = 'negative' "
        "AND events.date BETWEEN ? AND ? "
        "ORDER BY events.date, events.time",
        (user_id, date_from, date_to),
    ).fetchall()


def get_event_if_visible(
    conn: sqlite3.Connection, event_id: int, requesting_user_id: int
) -> sqlite3.Row | None:
    """Renvoie l'événement s'il appartient au demandeur ou s'il est public, sinon None."""
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if row is None:
        return None
    if row["user_id"] != requesting_user_id and row["visibility"] != "public":
        return None
    return row


def list_recent_events_for_user(
    conn: sqlite3.Connection, user_id: int, limit: int = 20
) -> list[sqlite3.Row]:
    """Événements les plus récents de l'utilisateur, pour choisir une cause dans le formulaire."""
    return conn.execute(
        "SELECT * FROM events WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


def build_event_view(
    conn: sqlite3.Connection, row: sqlite3.Row, requesting_user_id: int
) -> dict:
    """Assemble le contexte d'affichage d'un événement : entrée, besoins, cause liée, émotion."""
    caused_by = None
    if row["caused_by_event_id"] is not None:
        caused_by = get_event_if_visible(conn, row["caused_by_event_id"], requesting_user_id)
    emotion = None
    if row["emotion_id"] is not None:
        emotion = get_emotion_by_id(conn, row["emotion_id"])
    return {
        "entry": row,
        "entry_needs": get_needs_for_entry(conn, "event", row["id"]),
        "caused_by": caused_by,
        "emotion": emotion,
    }


# --- Goals --------------------------------------------------------------------


def create_goal(
    conn: sqlite3.Connection,
    user_id: int,
    date: date_type | str,
    label: str,
    visibility: str,
) -> sqlite3.Row:
    cur = conn.execute(
        "INSERT INTO daily_goals (user_id, date, label, visibility) VALUES (?, ?, ?, ?)",
        (user_id, str(date), label, visibility),
    )
    conn.commit()
    return conn.execute(
        "SELECT * FROM daily_goals WHERE id = ?", (cur.lastrowid,)
    ).fetchone()


def get_goal_if_visible(
    conn: sqlite3.Connection, goal_id: int, requesting_user_id: int
) -> sqlite3.Row | None:
    """Renvoie l'objectif s'il appartient au demandeur ou s'il est public, sinon None."""
    row = conn.execute("SELECT * FROM daily_goals WHERE id = ?", (goal_id,)).fetchone()
    if row is None:
        return None
    if row["user_id"] != requesting_user_id and row["visibility"] != "public":
        return None
    return row


def update_goal(
    conn: sqlite3.Connection,
    goal_id: int,
    user_id: int,
    label: str | None = None,
    done: bool | None = None,
) -> sqlite3.Row | None:
    """Met à jour le libellé et/ou l'état d'un objectif dont l'appelant est propriétaire."""
    row = conn.execute(
        "SELECT * FROM daily_goals WHERE id = ? AND user_id = ?", (goal_id, user_id)
    ).fetchone()
    if row is None:
        return None
    new_label = label if label is not None else row["label"]
    new_done = int(done) if done is not None else row["done"]
    conn.execute(
        "UPDATE daily_goals SET label = ?, done = ? WHERE id = ?",
        (new_label, new_done, goal_id),
    )
    conn.commit()
    return conn.execute(
        "SELECT * FROM daily_goals WHERE id = ?", (goal_id,)
    ).fetchone()


def delete_goal(conn: sqlite3.Connection, goal_id: int, user_id: int) -> bool:
    """Supprime un objectif dont l'appelant est propriétaire. Renvoie False si absent/non propriétaire."""
    row = conn.execute(
        "SELECT * FROM daily_goals WHERE id = ? AND user_id = ?", (goal_id, user_id)
    ).fetchone()
    if row is None:
        return False
    conn.execute("DELETE FROM daily_goals WHERE id = ?", (goal_id,))
    conn.commit()
    return True


def compute_goal_completion(
    conn: sqlite3.Connection, user_id: int, date: date_type | str
) -> tuple[int, int]:
    """Retourne (nb terminés, nb total) pour les objectifs de l'utilisateur ce jour-là."""
    row = conn.execute(
        "SELECT COUNT(*) AS total, SUM(done) AS done "
        "FROM daily_goals WHERE user_id = ? AND date = ?",
        (user_id, str(date)),
    ).fetchone()
    total = row["total"] or 0
    done = row["done"] or 0
    return done, total


# --- Shared tasks --------------------------------------------------------------


def list_tasks(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM shared_tasks ORDER BY status, created_at DESC"
    ).fetchall()


def create_task(
    conn: sqlite3.Connection, label: str, assigned_to: int | None
) -> sqlite3.Row:
    cur = conn.execute(
        "INSERT INTO shared_tasks (label, status, assigned_to, created_at) "
        "VALUES (?, 'todo', ?, ?)",
        (label, assigned_to, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    return conn.execute(
        "SELECT * FROM shared_tasks WHERE id = ?", (cur.lastrowid,)
    ).fetchone()


def update_task(
    conn: sqlite3.Connection, task_id: int, status: str, assigned_to: int | None
) -> sqlite3.Row | None:
    row = conn.execute(
        "SELECT * FROM shared_tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if row is None:
        return None
    conn.execute(
        "UPDATE shared_tasks SET status = ?, assigned_to = ? WHERE id = ?",
        (status, assigned_to, task_id),
    )
    conn.commit()
    return conn.execute(
        "SELECT * FROM shared_tasks WHERE id = ?", (task_id,)
    ).fetchone()
