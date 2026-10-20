"""User-scoped application event analytics on the existing SQLite product database.

Additive migration; no synthetic jobs, no automatic application submissions.
"""
from __future__ import annotations

import sqlite3
import time
import uuid

STAGES = ("saved", "applied", "screen", "interview", "final", "offer", "rejected", "withdrawn")
SOURCES = ("user", "email", "system", "import")

MIGRATION = """
CREATE TABLE IF NOT EXISTS user_application_events (
 id TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 job_id TEXT NOT NULL,
 event_key TEXT NOT NULL,
 stage TEXT NOT NULL CHECK(stage IN ('saved','applied','screen','interview','final','offer','rejected','withdrawn')),
 source TEXT NOT NULL CHECK(source IN ('user','email','system','import')),
 confirmed INTEGER NOT NULL DEFAULT 0 CHECK(confirmed IN (0,1)),
 occurred_at REAL NOT NULL,
 recorded_at REAL NOT NULL,
 UNIQUE(user_id,job_id,event_key)
);
CREATE INDEX IF NOT EXISTS idx_user_application_events_history
 ON user_application_events(user_id,job_id,occurred_at,id);
"""

def migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(MIGRATION)

def record_event(conn: sqlite3.Connection, user_id: str, job_id: str, event_key: str,
                 stage: str, source: str, confirmed: bool = False,
                 occurred_at: float | None = None) -> dict:
    if stage not in STAGES or source not in SOURCES:
        raise ValueError("Invalid application stage or source")
    if not all(isinstance(x, str) and x.strip() for x in (user_id, job_id, event_key)):
        raise ValueError("Missing event identity")
    # Prevent orphaned events and cross-user job references.
    if not conn.execute("SELECT 1 FROM user_jobs WHERE user_id=? AND job_id=?",
                        (user_id, job_id)).fetchone():
        raise ValueError("Job not found for user")
    now = time.time()
    conn.execute("""INSERT INTO user_application_events
      (id,user_id,job_id,event_key,stage,source,confirmed,occurred_at,recorded_at)
      VALUES (?,?,?,?,?,?,?,?,?)
      ON CONFLICT(user_id,job_id,event_key) DO NOTHING""",
      (uuid.uuid4().hex, user_id, job_id, event_key, stage, source,
       int(confirmed), now if occurred_at is None else occurred_at, now))
    conn.commit()
    row = conn.execute("""SELECT * FROM user_application_events
      WHERE user_id=? AND job_id=? AND event_key=?""",
      (user_id, job_id, event_key)).fetchone()
    return dict(row)

def timeline(conn: sqlite3.Connection, user_id: str, job_id: str) -> list[dict]:
    return [dict(row) for row in conn.execute("""SELECT * FROM user_application_events
      WHERE user_id=? AND job_id=? ORDER BY occurred_at,id""", (user_id, job_id))]

def funnel(conn: sqlite3.Connection, user_id: str) -> dict[str, int]:
    # Reach is distinct per job and stage; unconfirmed inferences are excluded.
    counts = {stage: 0 for stage in ("applied", "screen", "interview", "final", "offer")}
    rows = conn.execute("""SELECT stage,COUNT(DISTINCT job_id) AS n
      FROM user_application_events WHERE user_id=? AND confirmed=1
      AND stage IN ('applied','screen','interview','final','offer')
      GROUP BY stage""", (user_id,))
    for row in rows:
        counts[row["stage"]] = row["n"]
    return counts
