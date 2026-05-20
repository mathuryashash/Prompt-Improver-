import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "history.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS optimizations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT    NOT NULL DEFAULT (datetime('now')),
                app_context TEXT    NOT NULL,
                raw_prompt  TEXT,
                opt_prompt  TEXT,
                action      TEXT    NOT NULL,
                final_text  TEXT,
                model       TEXT,
                latency_ms  INTEGER
            );

            CREATE TABLE IF NOT EXISTS persona_cache (
                app_context TEXT    PRIMARY KEY,
                summary     TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_opt_app_ts
                ON optimizations(app_context, timestamp);
        """)
        conn.execute(
            "DELETE FROM optimizations WHERE timestamp < datetime('now', '-90 days')"
        )
