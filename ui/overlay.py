import tkinter as tk
from tkinter import font as tkfont
from core.app_detector import AppContext

AUTO_DISMISS_SECONDS = 30

# Colour scheme
BG = "#1e1e2e"
BG_PANEL = "#2a2a3e"
FG = "#cdd6f4"
FG_DIM = "#6c7086"
ACCENT = "#89b4fa"
BTN_ACCEPT = "#a6e3a1"
BTN_EDIT = "#f9e2af"
BTN_DISMISS = "#f38ba8"
BTN_FG = "#1e1e2e"


def show_overlay(
    original: str,
    optimized: str,
    app_context: AppContext,
    model: str,
    latency_ms: int,
) -> dict:
    """
    Show the comparison overlay. Blocks until user acts or 30s timeout.
    Returns {"action": "accepted"|"edited"|"dismissed", "text": str}.
    """
    result = {"action": "dismissed", "text": original}

    root = tk.Tk()
    root.title("PromptImprover")
    root.configure(bg=BG)
    root.attributes("-topmost", True)
    root.resizable(True, True)

    _center_window(root, 640, 520)

    mono = tkfont.Font(family="Consolas", size=10)
    sans = tkfont.Font(family="Segoe UI", size=10)
    sans_bold = tkfont.Font(family="Segoe UI", size=10, weight="bold")
    small = tkfont.Font(family="Segoe UI", size=9)

    # ── Header ──────────────────────────────────────────────────────────────
    header = tk.Frame(root, bg=BG_PANEL, pady=8, padx=12)
    header.pack(fill="x")

    tk.Label(
        header,
        text=f"{app_context.icon}  {app_context.display_name}",
        bg=BG_PANEL, fg=FG, font=sans_bold,
    ).pack(side="left")

    latency_label = tk.Label(
        header,
        text=f"{model}  ·  {latency_ms / 1000:.1f}s",
        bg=BG_PANEL, fg=FG_DIM, font=small,
    )
    latency_label.pack(side="right")

    countdown_var = tk.StringVar(value=f"auto-dismiss in {AUTO_DISMISS_SECONDS}s")
    tk.Label(
        header,
        textvariable=countdown_var,
        bg=BG_PANEL, fg=FG_DIM, font=small,
    ).pack(side="right", padx=12)

    # ── Body ─────────────────────────────────────────────────────────────────
    body = tk.Frame(root, bg=BG, padx=12, pady=8)
    body.pack(fill="both", expand=True)

    tk.Label(body, text="ORIGINAL", bg=BG, fg=FG_DIM, font=small, anchor="w").pack(fill="x")
    orig_box = _scrolled_text(body, mono, readonly=True)
    orig_box.insert("1.0", original)
    orig_box.config(state="disabled")
    orig_box.pack(fill="both", expand=True, pady=(0, 8))

    tk.Label(body, text="OPTIMIZED", bg=BG, fg=ACCENT, font=small, anchor="w").pack(fill="x")
    opt_box = _scrolled_text(body, mono, readonly=True)
    opt_box.insert("1.0", optimized)
    opt_box.config(state="disabled")
    opt_box.pack(fill="both", expand=True)

    # ── Button bar ───────────────────────────────────────────────────────────
    btn_bar = tk.Frame(root, bg=BG_PANEL, pady=10, padx=12)
    btn_bar.pack(fill="x")

    is_editing = [False]

    def do_accept():
        result["action"] = "accepted"
        result["text"] = opt_box.get("1.0", "end-1c")
        root.destroy()

    def do_edit():
        is_editing[0] = True
        opt_box.config(state="normal", bg="#2e2e42")
        opt_box.focus_set()
        edit_btn.config(state="disabled")
        accept_btn.config(text="Accept ↵ (edited)")

    def do_dismiss():
        if is_editing[0]:
            current_text = opt_box.get("1.0", "end-1c")
            if current_text != optimized:  # content changed
                import tkinter.messagebox as mb
                if not mb.askyesno(
                    "Discard edits?",
                    "You have unsaved edits. Discard them?",
                    parent=root,
                ):
                    return  # user said No — stay in overlay
        result["action"] = "dismissed"
        result["text"] = original
        root.destroy()

    accept_btn = tk.Button(
        btn_bar, text="Accept ↵", command=do_accept,
        bg=BTN_ACCEPT, fg=BTN_FG, font=sans_bold,
        relief="flat", padx=16, pady=6, cursor="hand2",
    )
    accept_btn.pack(side="left", padx=(0, 6))

    edit_btn = tk.Button(
        btn_bar, text="Edit  Ctrl+E", command=do_edit,
        bg=BTN_EDIT, fg=BTN_FG, font=sans_bold,
        relief="flat", padx=16, pady=6, cursor="hand2",
    )
    edit_btn.pack(side="left", padx=(0, 6))

    tk.Button(
        btn_bar, text="Dismiss  Esc", command=do_dismiss,
        bg=BTN_DISMISS, fg=BTN_FG, font=sans_bold,
        relief="flat", padx=16, pady=6, cursor="hand2",
    ).pack(side="left")

    # ── Keyboard shortcuts ───────────────────────────────────────────────────
    root.bind("<Return>", lambda _: do_accept())
    root.bind("<Escape>", lambda _: do_dismiss())
    root.bind("<Control-e>", lambda _: do_edit())

    # ── Auto-dismiss countdown ───────────────────────────────────────────────
    remaining = [AUTO_DISMISS_SECONDS]

    def tick():
        remaining[0] -= 1
        if remaining[0] <= 0:
            do_dismiss()
            return
        countdown_var.set(f"auto-dismiss in {remaining[0]}s")
        root.after(1000, tick)

    def reset_countdown(event=None):
        remaining[0] = AUTO_DISMISS_SECONDS

    root.bind("<Motion>", reset_countdown)
    root.bind("<Key>", reset_countdown)
    root.bind("<Button>", reset_countdown)
    root.after(1000, tick)

    root.focus_force()
    root.mainloop()

    # If edit mode was active, capture whatever is in the box
    if result["action"] == "accepted":
        pass  # already captured in do_accept

    return result


def _scrolled_text(parent, font, readonly=False) -> tk.Text:
    frame = tk.Frame(parent, bg=BG_PANEL)
    frame.pack(fill="both", expand=True)

    sb = tk.Scrollbar(frame)
    sb.pack(side="right", fill="y")

    txt = tk.Text(
        frame,
        font=font,
        bg=BG_PANEL,
        fg=FG,
        insertbackground=FG,
        selectbackground=ACCENT,
        selectforeground=BTN_FG,
        relief="flat",
        wrap="word",
        yscrollcommand=sb.set,
        padx=8,
        pady=6,
        height=6,
    )
    txt.pack(side="left", fill="both", expand=True)
    sb.config(command=txt.yview)
    return txt


def _center_window(win: tk.Tk, w: int, h: int):
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 3  # slightly above centre feels more natural
    win.geometry(f"{w}x{h}+{x}+{y}")
