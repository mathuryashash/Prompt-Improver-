import json
import datetime
import requests
from learning.history import get_recent, has_enough_samples
from learning.db import get_connection

CACHE_TTL_SECONDS = 600  # 10 minutes


def get_history_signal(app_context: str, config, min_samples: int = 5) -> str | None:
    if not has_enough_samples(app_context, min_samples):
        return None

    cached = _get_cached_summary(app_context)
    if cached:
        return cached

    recent = get_recent(app_context, limit=20)
    summary = _generate_summary(recent, app_context, config)
    _cache_summary(app_context, summary)
    return summary


def _generate_summary(records: list[dict], app_context: str, config) -> str:
    accepted = [r for r in records if r["action"] in ("accepted", "edited")]
    dismissed = [r for r in records if r["action"] == "dismissed"]

    prompt = (
        f"You are analyzing how a user interacts with an AI prompt optimizer in {app_context}.\n\n"
        f"Recent optimization history (last {len(records)} interactions):\n"
        f"- Accepted/Edited: {len(accepted)} times\n"
        f"- Dismissed: {len(dismissed)} times\n\n"
        "Sample accepted prompts (what the user liked):\n"
        f"{json.dumps([r['opt_prompt'][:200] for r in accepted[:5]], indent=2)}\n\n"
        "Sample dismissed prompts (what the user rejected):\n"
        f"{json.dumps([r['opt_prompt'][:200] for r in dismissed[:3]], indent=2)}\n\n"
        "In ONE sentence, describe what kinds of optimizations this user tends to accept vs. reject. "
        "Be specific and actionable. Example: \"User tends to accept prompts that specify output format "
        "and reject ones that add unnecessary verbosity.\"\n\n"
        "Summary:"
    )

    try:
        if config.backend == "ollama":
            resp = requests.post(
                f"{config.host}/api/generate",
                json={"model": config.model_name, "prompt": prompt, "stream": False},
                timeout=config.timeout,
            )
            resp.raise_for_status()
            return resp.json()["response"].strip()
        elif config.backend == "lmstudio":
            resp = requests.post(
                f"{config.host}/v1/chat/completions",
                json={
                    "model": config.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.3,
                },
                timeout=config.timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass

    return f"User has accepted {len(accepted)} of {len(records)} optimizations in {app_context}."


def _get_cached_summary(app_context: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT summary, updated_at FROM persona_cache WHERE app_context = ?",
            (app_context,),
        ).fetchone()
    if not row:
        return None
    updated = datetime.datetime.fromisoformat(row["updated_at"])
    age = (datetime.datetime.utcnow() - updated).total_seconds()
    if age > CACHE_TTL_SECONDS:
        return None
    return row["summary"]


def _cache_summary(app_context: str, summary: str):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO persona_cache(app_context, summary)
               VALUES (?, ?)
               ON CONFLICT(app_context) DO UPDATE SET
                   summary = excluded.summary,
                   updated_at = datetime('now')""",
            (app_context, summary),
        )
