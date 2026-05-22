"""
RightClickListener — pure Win32 mouse hook (no pynput).
Works on Python 3.13+ where pynput's threading._handle conflicts.

Uses SetWindowsHookExW(WH_MOUSE_LL) via ctypes.
"""
import ctypes
import ctypes.wintypes as wt
import queue
import threading

WH_MOUSE_LL  = 14
WM_RBUTTONDOWN = 0x0204
HC_ACTION    = 0

user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Use LPARAM (c_ssize_t) for lParam — it's a pointer on 64-bit Windows.
LPARAM   = ctypes.c_ssize_t
WPARAM   = ctypes.c_size_t
HOOKPROC = ctypes.WINFUNCTYPE(LPARAM, ctypes.c_int, WPARAM, LPARAM)

# Explicit argtypes prevent 64-bit overflow when ctypes marshals values.
user32.CallNextHookEx.argtypes = [wt.HANDLE, ctypes.c_int, WPARAM, LPARAM]
user32.CallNextHookEx.restype  = LPARAM
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype  = wt.HANDLE
user32.GetMessageW.argtypes  = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.GetMessageW.restype   = ctypes.c_int
user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, WPARAM, LPARAM]
user32.PostThreadMessageW.restype  = wt.BOOL


class _MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt",          wt.POINT),
        ("mouseData",   wt.DWORD),
        ("flags",       wt.DWORD),
        ("time",        wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wt.ULONG)),
    ]


class RightClickListener:
    """
    Installs a WH_MOUSE_LL hook that fires a ('right_click', x, y) event
    into *event_queue* whenever the right mouse button is pressed down.
    """

    def __init__(self, event_queue: queue.Queue):
        self._queue   = event_queue
        self._hook    = None
        self._proc    = None
        self._thread  = None
        self._stop_ev = threading.Event()

    def _make_proc(self):
        def _hook_proc(nCode, wParam, lParam):
            if nCode == HC_ACTION and wParam == WM_RBUTTONDOWN:
                ms = ctypes.cast(lParam, ctypes.POINTER(_MSLLHOOKSTRUCT)).contents
                try:
                    self._queue.put_nowait(("right_click", ms.pt.x, ms.pt.y))
                except queue.Full:
                    pass
            return user32.CallNextHookEx(None, nCode, wParam, lParam)
        return HOOKPROC(_hook_proc)

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="RightClickListener")
        self._thread.start()

    def _run(self):
        self._proc = self._make_proc()
        # For WH_MOUSE_LL the hMod param MUST be None when the hook
        # proc lives inside the current process (not a separate DLL).
        self._hook = user32.SetWindowsHookExW(
            WH_MOUSE_LL, self._proc, None, 0
        )
        if not self._hook:
            err = kernel32.GetLastError()
            raise RuntimeError(f"Failed to install mouse hook (GetLastError={err})")

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
