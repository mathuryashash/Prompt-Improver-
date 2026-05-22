import ctypes
import threading
import tkinter as tk

# Win32 constants to make the popup non-focus-stealing
_GWL_EXSTYLE = -20
_WS_EX_NOACTIVATE = 0x08000000
_WS_EX_TOPMOST = 0x00000008


def _make_no_activate(win: tk.Tk):
    """Prevent the window from stealing focus when shown or clicked."""
    hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
    if hwnd == 0:
        hwnd = win.winfo_id()
    style = ctypes.windll.user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(hwnd, _GWL_EXSTYLE,
                                        style | _WS_EX_NOACTIVATE | _WS_EX_TOPMOST)


def show_optimize_button(x: int, y: int) -> bool:
    """
    Show a tiny non-focus-stealing 'Optimize' button near (x, y).
    The original window keeps focus throughout — text stays selected.
    Returns True if the user clicked Optimize, False if dismissed.
    Auto-dismisses after 2.5 seconds.
    """
    clicked = [False]

    win = tk.Tk()
    win.overrideredirect(True)   # no title bar, no borders
    win.attributes("-topmost", True)
    win.configure(bg="#1e1e2e")

    # Draw a subtle rounded-looking border via a frame
    outer = tk.Frame(win, bg="#89b4fa", padx=1, pady=1)
    outer.pack()

    inner = tk.Frame(outer, bg="#1e1e2e", padx=0, pady=0)
    inner.pack()

    def on_optimize():
        clicked[0] = True
        win.destroy()

    btn = tk.Button(
        inner,
        text="⚡  Optimize",
        command=on_optimize,
        bg="#1e1e2e",
        fg="#89b4fa",
        font=("Segoe UI", 10, "bold"),
        relief="flat",
        padx=14,
        pady=7,
        cursor="hand2",
        activebackground="#2a2a3e",
        activeforeground="#89b4fa",
        bd=0,
    )
    btn.pack()

    # Position left of cursor, keep within screen bounds
    win.update_idletasks()
    w = win.winfo_reqwidth()
    h = win.winfo_reqheight()
    sh = win.winfo_screenheight()
    px = max(x - w - 12, 8)
    py = min(y + 12, sh - h - 8)
    win.geometry(f"+{px}+{py}")

    # Apply no-activate AFTER the window is positioned and visible
    win.update()
    _make_no_activate(win)

    # Auto-dismiss
    win.after(2500, win.destroy)
    win.bind("<Escape>", lambda _: win.destroy())

    win.mainloop()
    return clicked[0]


class LoadingIndicator:
    """
    Shows a tiny non-focus-stealing window near the cursor with a rotating
    spinner canvas and text indicating prompt enhancement is in progress.
    Runs on its own thread to ensure smooth animation while the main thread blocks/works.
    """
    def __init__(self, x: int, y: int, app_name: str):
        self.x = x
        self.y = y
        self.app_name = app_name
        self.win = None
        self.thread = None
        self.stop_event = threading.Event()
        self.angle = 0

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        self.win = tk.Tk()
        self.win.overrideredirect(True)   # no title bar, no borders
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#1e1e2e")

        # Draw a subtle rounded-looking border via a frame
        outer = tk.Frame(self.win, bg="#89b4fa", padx=1, pady=1)
        outer.pack()

        inner = tk.Frame(outer, bg="#1e1e2e", padx=12, pady=10)
        inner.pack()

        # Canvas for custom smooth arc-based spinner
        self.canvas = tk.Canvas(inner, width=20, height=20, bg="#1e1e2e", highlightthickness=0)
        self.canvas.pack(side="left", padx=(0, 10))

        # Text labels
        lbl_frame = tk.Frame(inner, bg="#1e1e2e")
        lbl_frame.pack(side="left")

        tk.Label(
            lbl_frame,
            text="Enhancing prompt...",
            bg="#1e1e2e",
            fg="#cdd6f4",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            lbl_frame,
            text=f"Target: {self.app_name}",
            bg="#1e1e2e",
            fg="#6c7086",
            font=("Segoe UI", 8),
            anchor="w",
        ).pack(fill="x")

        # Position to the left of the cursor, keep within screen bounds
        self.win.update_idletasks()
        w = self.win.winfo_reqwidth()
        h = self.win.winfo_reqheight()
        sh = self.win.winfo_screenheight()

        px = max(self.x - w - 12, 8)
        py = min(self.y + 12, sh - h - 8)
        self.win.geometry(f"+{px}+{py}")

        # Apply no-activate AFTER the window is positioned and visible
        self.win.update()
        _make_no_activate(self.win)

        def animate():
            if self.stop_event.is_set():
                try:
                    self.win.destroy()
                except Exception:
                    pass
                return
            try:
                self.canvas.delete("spinner")
                # Draw thick rotating arc using accent color
                self.canvas.create_arc(
                    2, 2, 18, 18,
                    start=self.angle,
                    extent=120,
                    outline="#89b4fa",
                    width=3,
                    tags="spinner",
                )
                self.angle = (self.angle + 15) % 360
                self.win.after(30, animate)
            except Exception:
                pass

        self.win.after(30, animate)
        self.win.mainloop()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=0.5)

