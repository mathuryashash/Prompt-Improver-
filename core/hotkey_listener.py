import queue
from pynput import keyboard


class HotkeyListener:
    def __init__(self, hotkey_str: str, event_queue: queue.Queue):
        self._queue = event_queue
        self._hotkey_str = self._parse(hotkey_str)
        self._listener = None

    def _parse(self, s: str) -> str:
        parts = s.split("+")

        def fmt(p: str) -> str:
            p = p.strip().lower()
            return f"<{p}>" if p in ("ctrl", "shift", "alt", "cmd", "win") else p

        return "+".join(fmt(p) for p in parts)

    def start(self):
        hotkeys = {self._hotkey_str: self._on_activate}
        self._listener = keyboard.GlobalHotKeys(hotkeys)
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()

    def _on_activate(self):
        self._queue.put("hotkey")
