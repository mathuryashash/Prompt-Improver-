"""
test_hooks.py — Isolated test for the new ctypes Win32 hook listeners.

Tests:
  1. HotkeyListener starts without error and installs its WH_KEYBOARD_LL hook.
  2. RightClickListener starts without error and installs its WH_MOUSE_LL hook.
  3. Both stop cleanly via stop() + thread join.
  4. Listener threads are no longer alive after stop().
  5. Full system check still passes (regression guard).

Run from the project root:
  d:\\promptimprover\\.venv\\Scripts\\python.exe test_hooks.py
"""
import sys
import time
import queue
import threading
import traceback
import os

# ── path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, r"d:\promptimprover")
os.chdir(r"d:\promptimprover")

PASS = "  ✓"
FAIL = "  ✗"

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


# ── 1. HotkeyListener start/stop ──────────────────────────────────────────────
def t_hotkey_listener():
    from core.hotkey_listener import HotkeyListener
    q = queue.Queue()
    hl = HotkeyListener("ctrl+shift+.", q)
    hl.start()

    # Give the hook thread time to install
    time.sleep(0.5)

    assert hl._thread is not None, "Thread was never created"
    assert hl._thread.is_alive(), "Listener thread died on startup"
    assert hl._hook, "Hook handle is falsy — SetWindowsHookExW failed"

    hl.stop()
    hl._thread.join(timeout=2.0)
    assert not hl._thread.is_alive(), "Listener thread did not stop within 2 s"
    return f"hook=0x{hl._hook:X}, thread stopped cleanly"

test("HotkeyListener installs WH_KEYBOARD_LL hook + stops cleanly", t_hotkey_listener)


# ── 2. RightClickListener start/stop ──────────────────────────────────────────
def t_mouse_listener():
    from core.mouse_listener import RightClickListener
    q = queue.Queue()
    rl = RightClickListener(q)
    rl.start()

    time.sleep(0.5)

    assert rl._thread is not None, "Thread was never created"
    assert rl._thread.is_alive(), "Listener thread died on startup"
    assert rl._hook, "Hook handle is falsy — SetWindowsHookExW failed"

    rl.stop()
    rl._thread.join(timeout=2.0)
    assert not rl._thread.is_alive(), "Listener thread did not stop within 2 s"
    return f"hook=0x{rl._hook:X}, thread stopped cleanly"

test("RightClickListener installs WH_MOUSE_LL hook + stops cleanly", t_mouse_listener)


# ── 3. Both listeners run concurrently without interfering ───────────────────
def t_concurrent():
    from core.hotkey_listener import HotkeyListener
    from core.mouse_listener import RightClickListener
    q = queue.Queue()
    hl = HotkeyListener("ctrl+shift+.", q)
    rl = RightClickListener(q)
    hl.start()
    rl.start()
    time.sleep(0.5)

    assert hl._thread.is_alive(), "HotkeyListener thread died"
    assert rl._thread.is_alive(), "RightClickListener thread died"
    assert hl._hook, "Keyboard hook handle invalid"
    assert rl._hook, "Mouse hook handle invalid"

    hl.stop()
    rl.stop()
    hl._thread.join(timeout=2.0)
    rl._thread.join(timeout=2.0)
    assert not hl._thread.is_alive(), "HotkeyListener did not stop"
    assert not rl._thread.is_alive(), "RightClickListener did not stop"
    return "both hooks active simultaneously, both stopped cleanly"

test("Both listeners run concurrently without interference", t_concurrent)


# ── 4. Queue receives no phantom events on idle ───────────────────────────────
def t_no_phantom_events():
    from core.hotkey_listener import HotkeyListener
    from core.mouse_listener import RightClickListener
    q = queue.Queue()
    hl = HotkeyListener("ctrl+shift+.", q)
    rl = RightClickListener(q)
    hl.start()
    rl.start()
    time.sleep(0.3)

    events = []
    while not q.empty():
        events.append(q.get_nowait())

    hl.stop()
    rl.stop()
    hl._thread.join(timeout=2.0)
    rl._thread.join(timeout=2.0)

    assert len(events) == 0, f"Unexpected phantom events: {events}"
    return "queue empty after 300 ms idle (no phantom events)"

test("No phantom events fired on idle", t_no_phantom_events)


# ── 5. Core system regression check ──────────────────────────────────────────
def t_system_regression():
    from core.config import load_config
    from core.app_detector import AppContext, APP_CONVENTIONS
    from core.optimizer import Optimizer

    cfg = load_config()
    opt = Optimizer(cfg)
    from core.app_detector import detect
    ctx = detect()
    msgs = opt._build_messages(
        raw="test prompt",
        ctx=ctx,
        role=cfg.persona_role,
        domain=cfg.persona_domain,
        style=cfg.persona_style,
        signal=None,
    )
    assert len(msgs) >= 2
    assert msgs[0]["role"] == "system"
    assert msgs[-1]["role"] == "user"
    return f"Optimizer message chain: {len(msgs)} messages, system+user structure OK"

test("Optimizer message chain regression check", t_system_regression)


# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("=" * 60)
passed = sum(1 for r in results if r[0])
failed = sum(1 for r in results if not r[0])
print(f"Hook Test Results: {passed} passed  |  {failed} failed")
print("=" * 60)

if failed > 0:
    sys.exit(1)
