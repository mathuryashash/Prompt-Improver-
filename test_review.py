"""
PromptImprover — automated review test script.
Tests all components that can be exercised without a running Ollama instance.
"""
import sys
import time
import traceback

PASS = "  ✓"
FAIL = "  ✗"
WARN = "  ⚠"

results = []


def test(name, fn):
    try:
        msg = fn()
        results.append((True, name, msg or ""))
        print(f"{PASS} {name}" + (f" — {msg}" if msg else ""))
    except Exception as e:
        results.append((False, name, str(e)))
        print(f"{FAIL} {name} — {e}")
        traceback.print_exc()


# ── 1. Config ────────────────────────────────────────────────────────────────

def t_config():
    from core.config import load_config
    cfg = load_config()
    assert cfg.hotkey == "ctrl+shift+."
    assert cfg.backend in ("ollama", "lmstudio")
    assert cfg.model_name
    assert cfg.persona_role
    return f"hotkey={cfg.hotkey}, model={cfg.model_name}, backend={cfg.backend}"

test("Config loads correctly", t_config)


# ── 2. Database ───────────────────────────────────────────────────────────────

def t_db_init():
    from learning.db import init_db, get_connection
    init_db()
    with get_connection() as conn:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
    assert "optimizations" in tables, f"Missing table 'optimizations', found: {tables}"
    assert "persona_cache" in tables, f"Missing table 'persona_cache', found: {tables}"
    return f"tables={tables}"

test("DB initialises (both tables present)", t_db_init)


def t_db_record_and_query():
    from learning.db import init_db, get_connection
    from learning.history import record, get_recent, acceptance_rate, OptRecord
    init_db()
    # Write a test record
    record(OptRecord(
        app_context="test_app",
        raw_prompt="make a sort function",
        opt_prompt="Write a Python function that sorts a list of dicts by 'created_at' descending.",
        action="accepted",
        final_text="Write a Python function that sorts a list of dicts by 'created_at' descending.",
        model="llama3.2:3b",
        latency_ms=1234,
    ))
    # Read it back
    rows = get_recent("test_app", limit=5)
    assert len(rows) >= 1, "No rows returned after insert"
    rate = acceptance_rate("test_app")
    assert 0.0 <= rate <= 1.0, f"Acceptance rate out of range: {rate}"
    return f"rows={len(rows)}, acceptance_rate={rate:.0%}"

test("DB write + read + acceptance_rate", t_db_record_and_query)


# ── 3. App Detector ───────────────────────────────────────────────────────────

def t_app_detector():
    from core.app_detector import _classify, detect, APP_CONVENTIONS, DISPLAY_NAMES, ICONS
    # Classification logic
    assert _classify("chrome.exe", "claude.ai - claude") == "claude_web"
    assert _classify("opencode.exe", "") == "opencode"
    assert _classify("notepad.exe", "untitled") == "generic"
    assert _classify("hermes.exe", "") == "hermes"
    # Detect actual foreground window (won't crash)
    ctx = detect()
    assert ctx.id in APP_CONVENTIONS
    assert ctx.display_name in DISPLAY_NAMES.values()
    assert ctx.icon in ICONS.values()
    return f"detected foreground as '{ctx.id}' ({ctx.display_name})"

test("App detector classifies correctly + detects foreground", t_app_detector)


# ── 4. Optimizer message builder (no LLM call) ────────────────────────────────

def t_optimizer_messages():
    from core.config import load_config
    from core.app_detector import AppContext, APP_CONVENTIONS
    from core.optimizer import Optimizer

    cfg = load_config()
    opt = Optimizer(cfg)

    ctx = AppContext(
        id="claude_web",
        display_name="Claude (Web)",
        icon="🌐",
        conventions=APP_CONVENTIONS["claude_web"],
    )

    messages = opt._build_messages(
        raw="write a function to parse json",
        ctx=ctx,
        role=cfg.persona_role,
        domain=cfg.persona_domain,
        style=cfg.persona_style,
        signal=None,
    )

    assert len(messages) >= 2, "Too few messages built"
    assert messages[0]["role"] == "system", "First message must be system"
    # Last message must contain the raw prompt
    last = messages[-1]["content"]
    assert "write a function to parse json" in last, "Raw prompt missing from last message"
    return f"{len(messages)} messages built, last role={messages[-1]['role']}"

test("Optimizer builds correct message chain", t_optimizer_messages)


# ── 5. Prompt extraction / noise stripping ────────────────────────────────────

def t_extract_optimized():
    from core.optimizer import _extract_optimized_prompt

    # Standard format
    raw = "ANALYSIS:\n- vague task\n- no type hints\n\nOPTIMIZED PROMPT:\nWrite a Python function..."
    result = _extract_optimized_prompt(raw)
    assert result == "Write a Python function...", f"Got: {repr(result)}"

    # With trailing noise
    raw2 = "OPTIMIZED PROMPT:\nWrite a Python function...\nNote: this is a good prompt."
    result2 = _extract_optimized_prompt(raw2)
    assert "Note:" not in result2, f"Noise not stripped: {repr(result2)}"

    # Fallback — no markers
    raw3 = "Write a Python function to sort a list."
    result3 = _extract_optimized_prompt(raw3)
    assert "Write" in result3, f"Fallback failed: {repr(result3)}"

    return "standard / noise-stripping / fallback all pass"

test("Prompt extraction + noise stripping", t_extract_optimized)


# ── 6. Text capture (clipboard mechanics) ────────────────────────────────────

def t_clipboard():
    import pyperclip
    original = pyperclip.paste()
    pyperclip.copy("test_prompt_capture_12345")
    val = pyperclip.paste()
    assert val == "test_prompt_capture_12345", f"Clipboard read back wrong: {repr(val)}"
    # Restore
    try:
        pyperclip.copy(original)
    except Exception:
        pass
    return "clipboard read/write OK"

test("Clipboard read/write (pyperclip)", t_clipboard)


# ── 7. Learning / profile signal ─────────────────────────────────────────────

def t_history_signal_cold():
    from core.config import load_config
    from learning.profile import get_history_signal
    cfg = load_config()
    # 'test_app' has < 5 samples of a different kind — should return None (cold start)
    result = get_history_signal("nonexistent_app_xyz", cfg, min_samples=5)
    assert result is None, f"Expected None on cold start, got: {result}"
    return "returns None when < min_samples (cold start correct)"

test("History signal returns None on cold start", t_history_signal_cold)


# ── 8. Ollama connectivity ────────────────────────────────────────────────────

def t_ollama():
    import requests
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        return f"RUNNING — models: {models}"
    except Exception as e:
        # Not a hard failure — app gracefully shows error overlay
        return f"NOT RUNNING ({type(e).__name__}) — app will show error overlay (expected)"

# Mark as warning-level
try:
    import requests
    r = requests.get("http://localhost:11434/api/tags", timeout=3)
    models = [m["name"] for m in r.json().get("models", [])]
    print(f"{PASS} Ollama connectivity — RUNNING, models: {models}")
    results.append((True, "Ollama connectivity", f"models={models}"))
except Exception as e:
    print(f"{WARN} Ollama connectivity — NOT RUNNING (app will show error overlay gracefully)")
    results.append((None, "Ollama connectivity", "not running — non-fatal"))


# ── Summary ───────────────────────────────────────────────────────────────────

print()
print("=" * 56)
passed = sum(1 for r in results if r[0] is True)
warned = sum(1 for r in results if r[0] is None)
failed = sum(1 for r in results if r[0] is False)
print(f"Results: {passed} passed  |  {warned} warnings  |  {failed} failed")
print("=" * 56)

if failed > 0:
    sys.exit(1)
