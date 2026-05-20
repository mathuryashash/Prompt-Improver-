import queue
import threading
import subprocess
import winreg
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

APP_NAME = "PromptImprover"
ICON_PATH = Path(__file__).parent.parent / "assets" / "icon.png"


def run_tray(paused: threading.Event, event_queue: queue.Queue):
    """Runs the system tray. Intended to run in a daemon thread."""
    icon_image = _load_or_generate_icon()

    enabled_state = {"value": True}

    def toggle_enabled(icon, item):
        enabled_state["value"] = not enabled_state["value"]
        if enabled_state["value"]:
            paused.clear()
            icon.notify("PromptImprover enabled", "Hotkey is active.")
        else:
            paused.set()
            icon.notify("PromptImprover paused", "Hotkey is suspended.")

    def open_config(icon, item):
        config_path = Path(__file__).parent.parent / "config.toml"
        subprocess.Popen(["notepad.exe", str(config_path)])

    def view_history(icon, item):
        event_queue.put("show_history")

    def quit_app(icon, item):
        icon.stop()
        event_queue.put("quit")

    def enabled_checked(item):
        return enabled_state["value"]

    menu = pystray.Menu(
        pystray.MenuItem(APP_NAME, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Enabled", toggle_enabled, checked=enabled_checked),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Edit Persona / Settings", open_config),
        pystray.MenuItem("View History", view_history),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", quit_app),
    )

    icon = pystray.Icon(APP_NAME, icon_image, APP_NAME, menu)
    icon.run()


def _load_or_generate_icon() -> Image.Image:
    if ICON_PATH.exists():
        return Image.open(ICON_PATH).resize((64, 64))
    return _generate_icon()


def _generate_icon() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Circle background
    draw.ellipse([2, 2, size - 2, size - 2], fill="#89b4fa")

    # Simple "P" letter
    cx, cy = size // 2, size // 2
    draw.rectangle([cx - 10, cy - 16, cx - 4, cy + 16], fill="#1e1e2e")
    draw.ellipse([cx - 10, cy - 16, cx + 10, cy], fill="#1e1e2e")
    draw.ellipse([cx - 6, cy - 12, cx + 6, cy - 2], fill="#89b4fa")

    ICON_PATH.parent.mkdir(exist_ok=True)
    img.save(ICON_PATH)
    return img


# ── Windows startup registry helpers ─────────────────────────────────────────

def enable_startup():
    # run.pyw uses pythonw implicitly — no console window on boot
    app_path = str(Path(__file__).parent.parent / "run.pyw")
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'pythonw "{app_path}"')
    winreg.CloseKey(key)


def disable_startup():
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    try:
        winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
    winreg.CloseKey(key)
