"""
test_single_instance.py — Tests the Win32 named-mutex single-instance guard
without importing main.py (which would start pystray/tray threads).
"""
import sys, os, ctypes, traceback

PASS = "  ✓"
FAIL = "  ✗"
results = []

def test(name, fn):
    try:
        msg = fn()
        results.append((True, name, msg or ""))
        print(f"{PASS} {name}" + (f" - {msg}" if msg else ""))
    except Exception as e:
        results.append((False, name, str(e)))
        print(f"{FAIL} {name} - {e}")
        traceback.print_exc()

MUTEX_NAME   = "Global\\PromptImprover_SingleInstance"
ALREADY_EXISTS = 183

def _open():
    h   = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
    err = ctypes.windll.kernel32.GetLastError()
    return h, err

def _close(h):
    if h:
        ctypes.windll.kernel32.ReleaseMutex(h)
        ctypes.windll.kernel32.CloseHandle(h)

# 1. First instance acquires mutex
def t_first():
    h, err = _open()
    assert h and err != ALREADY_EXISTS
    _close(h)
    return "mutex acquired"
test("First instance acquires mutex", t_first)

# 2. Second instance is blocked while first holds it
def t_second():
    h1, _ = _open()
    h2, err2 = _open()
    blocked = (err2 == ALREADY_EXISTS)
    if h2: ctypes.windll.kernel32.CloseHandle(h2)
    _close(h1)
    assert blocked, f"Expected ALREADY_EXISTS, got err={err2}"
    return "second instance correctly blocked"
test("Second instance is blocked (duplicate tray prevented)", t_second)

# 3. After first exits, a new instance can start
def t_reacquire():
    h1, _ = _open()
    _close(h1)                # first exits
    h2, err2 = _open()
    ok = h2 and err2 != ALREADY_EXISTS
    _close(h2)
    assert ok, f"Re-acquisition failed err={err2}"
    return "re-acquisition after exit succeeds"
test("Re-acquisition after exit succeeds", t_reacquire)

# 4. _acquire_single_instance logic (inline, no main import)
def t_logic():
    def acquire(name):
        h   = ctypes.windll.kernel32.CreateMutexW(None, True, name)
        err = ctypes.windll.kernel32.GetLastError()
        if err == ALREADY_EXISTS:
            if h: ctypes.windll.kernel32.CloseHandle(h)
            return False, None
        return True, h

    ok1, h1 = acquire(MUTEX_NAME)
    assert ok1, "First call should return True"
    ok2, h2 = acquire(MUTEX_NAME)
    assert not ok2, "Second call should return False"
    _close(h1)
    return "_acquire_single_instance logic: True/False correct"
test("_acquire_single_instance() logic correct", t_logic)

print()
print("=" * 60)
passed = sum(1 for r in results if r[0])
failed = sum(1 for r in results if not r[0])
print(f"Single-Instance Results: {passed} passed  |  {failed} failed")
print("=" * 60)
if failed:
    sys.exit(1)
