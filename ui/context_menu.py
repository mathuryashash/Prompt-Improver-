import ctypes
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

    # Position near cursor, keep within screen bounds
    win.update_idletasks()
    w = win.winfo_reqwidth()
    h = win.winfo_reqheight()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    px = min(x + 12, sw - w - 8)
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
