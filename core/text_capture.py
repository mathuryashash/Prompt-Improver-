import time
import pyperclip
import pyautogui
import win32gui


def get_active_hwnd() -> int:
    """Return the handle of the currently focused window."""
    return win32gui.GetForegroundWindow()


def capture() -> str:
    """
    Captures text from the active input field via select-all + copy.
    Restores original clipboard on exit. Returns "" if nothing captured.
    """
    original_clipboard = _safe_get_clipboard()

    try:
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.15)

        captured = _safe_get_clipboard()
    finally:
        _safe_set_clipboard(original_clipboard)

    return captured if captured else ""


def inject(text: str, target_hwnd: int | None = None):
    """
    Replaces active field content with text via clipboard paste.
    If target_hwnd is given, focuses that window before pasting so the
    text lands in the original input, not whatever grabbed focus from the overlay.
    Restores original clipboard after injection.
    """
    if target_hwnd:
        try:
            win32gui.SetForegroundWindow(target_hwnd)
            time.sleep(0.15)  # let the OS complete the focus switch
        except Exception:
            pass  # non-fatal — best-effort focus restore

    original_clipboard = _safe_get_clipboard()
    try:
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
    finally:
        time.sleep(0.2)
        _safe_set_clipboard(original_clipboard)


def capture_field(target_hwnd: int | None = None) -> str:
    """
    Captures the full contents of an input field by selecting all then copying.
    Used for the right-click flow — focuses target_hwnd first so the original
    window receives the keystrokes (our context menu is non-focus-stealing, so
    the source window still has focus anyway, but we restore just to be safe).
    """
    if target_hwnd:
        try:
            win32gui.SetForegroundWindow(target_hwnd)
            time.sleep(0.1)
        except Exception:
            pass
    return capture()


def inject_paste(text: str, target_hwnd: int | None = None):
    """
    Paste text over the current selection without Ctrl+A first.
    Used when the user has text selected and we only want to replace the selection.
    Falls back to full-field inject if target_hwnd focus restore fails.
    """
    if target_hwnd:
        try:
            win32gui.SetForegroundWindow(target_hwnd)
            time.sleep(0.15)
        except Exception:
            pass

    original_clipboard = _safe_get_clipboard()
    try:
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
    finally:
        time.sleep(0.2)
        _safe_set_clipboard(original_clipboard)


def _safe_get_clipboard() -> str:
    try:
        return pyperclip.paste() or ""
    except Exception:
        return ""


def _safe_set_clipboard(text: str):
    try:
        pyperclip.copy(text)
    except Exception:
        pass
