"""
HotkeyListener — pure Win32 keyboard hook (no pynput).
Works on Python 3.13+ where pynput's threading._handle conflicts.

Uses SetWindowsHookExW(WH_KEYBOARD_LL) via ctypes so it has zero
external dependencies beyond the standard Windows DLLs.
"""
import ctypes
import ctypes.wintypes as wt
import queue
import threading

# Virtual key codes
_VK = {
    "ctrl":  0x11,  # VK_CONTROL (either Ctrl)
    "shift": 0x10,  # VK_SHIFT   (either Shift)
    "alt":   0x12,  # VK_MENU    (either Alt)
}

WH_KEYBOARD_LL = 13
WM_KEYDOWN     = 0x0100
WM_SYSKEYDOWN  = 0x0104
HC_ACTION      = 0

user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Use LPARAM (c_ssize_t) for lParam — it's a pointer on 64-bit Windows.
# Using c_long causes OverflowError when Windows passes a large 64-bit address.
LPARAM   = ctypes.c_ssize_t
WPARAM   = ctypes.c_size_t
HOOKPROC = ctypes.WINFUNCTYPE(LPARAM, ctypes.c_int, WPARAM, LPARAM)

# Tell ctypes the exact signature so it marshals 64-bit values correctly.
user32.CallNextHookEx.argtypes = [wt.HANDLE, ctypes.c_int, WPARAM, LPARAM]
user32.CallNextHookEx.restype  = LPARAM
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype  = wt.HANDLE
user32.GetMessageW.argtypes  = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.GetMessageW.restype   = ctypes.c_int
user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, WPARAM, LPARAM]
user32.PostThreadMessageW.restype  = wt.BOOL


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode",      wt.DWORD),
        ("scanCode",    wt.DWORD),
        ("flags",       wt.DWORD),
        ("time",        wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wt.ULONG)),
    ]


class HotkeyListener:
    """
    Installs a WH_KEYBOARD_LL hook that fires a 'hotkey' event into
    *event_queue* whenever the configured modifier+key combo is detected.

    hotkey_str examples: "ctrl+shift+.", "alt+h"
    """

    def __init__(self, hotkey_str: str, event_queue: queue.Queue):
        self._queue   = event_queue
        self._mods, self._trigger_vk = self._parse(hotkey_str)
        self._hook    = None
        self._proc    = None          # keep a reference — GC must not free it
        self._thread  = None
        self._stop_ev = threading.Event()

    # ------------------------------------------------------------------ parse
    def _parse(self, s: str):
        """Return (set_of_modifier_vks, trigger_vk_code)."""
        parts   = [p.strip().lower() for p in s.split("+")]
        mods    = set()
        trigger = None
        for p in parts:
            if p in _VK:
                mods.add(_VK[p])
            else:
                # Convert single char or named key
                if len(p) == 1:
                    trigger = user32.VkKeyScanA(ord(p)) & 0xFF
                else:
                    # Named keys like "period", "space" …
                    vk = user32.VkKeyScanA(ord(p[0])) & 0xFF
                    trigger = vk
        if trigger is None:
            raise ValueError(f"Cannot parse hotkey: {s!r}")
        return mods, trigger

    # ------------------------------------------------------------------ hook cb
    def _make_proc(self):
        def _hook_proc(nCode, wParam, lParam):
            if nCode == HC_ACTION and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                kb = ctypes.cast(lParam, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
                if kb.vkCode == self._trigger_vk:
                    if all(user32.GetAsyncKeyState(vk) & 0x8000 for vk in self._mods):
                        try:
                            self._queue.put_nowait("hotkey")
                        except queue.Full:
                            pass
            return user32.CallNextHookEx(None, nCode, wParam, lParam)
        return HOOKPROC(_hook_proc)

    # ------------------------------------------------------------------ start / stop
    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="HotkeyListener")
        self._thread.start()

    def _run(self):
        self._proc = self._make_proc()
        # For WH_KEYBOARD_LL the hMod param MUST be None when the hook
        # proc lives inside the current process (not a separate DLL).
        self._hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._proc, None, 0
        )
        if not self._hook:
            err = kernel32.GetLastError()
            raise RuntimeError(f"Failed to install keyboard hook (GetLastError={err})")

        # Blocking GetMessage pump — required for low-level hooks to fire.
        msg = wt.MSG()
        while not self._stop_ev.is_set():
            r = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if r == 0 or r == -1:   # WM_QUIT or error
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        user32.UnhookWindowsHookEx(self._hook)

    def stop(self):
        self._stop_ev.set()
        # Post WM_QUIT to unblock GetMessageW in the listener thread.
        if self._thread and self._thread.ident:
            user32.PostThreadMessageW(self._thread.ident, 0x0012, 0, 0)  # WM_QUIT
