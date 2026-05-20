import queue
from pynput import mouse


class RightClickListener:
    def __init__(self, event_queue: queue.Queue):
        self._queue = event_queue
        self._listener = None

    def start(self):
        self._listener = mouse.Listener(on_click=self._on_click)
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()

    def _on_click(self, x: int, y: int, button, pressed: bool):
        if button == mouse.Button.right and pressed:
            self._queue.put(("right_click", x, y))
