from dataclasses import dataclass
from learning.db import get_connection


@dataclass
class OptRecord:
    app_context: str
    raw_prompt: str
    opt_prompt: str
    action: str          # 'accepted' | 'edited' | 'dismissed'
    final_text: str | None
    model: str
    latency_ms: int


def record(r: OptRecord):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO optimizations
               (app_context, raw_prompt, opt_prompt, action, final_text, model, latency_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (r.app_context, r.raw_prompt, r.opt_prompt,
             r.action, r.final_text, r.model, r.latency_ms),
        )


def get_recent(app_context: str, limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT action, opt_prompt, final_text FROM optimizations
               WHERE app_context = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (app_context, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def has_enough_samples(app_context: str, min_count: int = 5) -> bool:
    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM optimizations WHERE app_context = ?",
            (app_context,),
        ).fetchone()[0]
    return count >= min_count


def acceptance_rate(app_context: str) -> float:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT
                COUNT(*) as total,
                SUM(CASE WHEN action IN ('accepted','edited') THEN 1 ELSE 0 END) as accepted
               FROM optimizations WHERE app_context = ?""",
            (app_context,),
        ).fetchone()
    if not row or row["total"] == 0:
        return 0.0
    return row["accepted"] / row["total"]
