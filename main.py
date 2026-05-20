import queue
import sys
import threading
import tkinter as tk

import requests.exceptions

from core.config import load_config
from core.hotkey_listener import HotkeyListener
from core.mouse_listener import RightClickListener
from core.text_capture import capture, capture_field, inject, inject_paste, get_active_hwnd
from core.app_detector import detect
from core.optimizer import Optimizer
from learning.db import init_db
from learning.history import record, OptRecord
from learning.profile import get_history_signal
from ui.overlay import show_overlay
from ui.context_menu import show_optimize_button
from ui.tray import run_tray


def main():
    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to parse config.toml: {e}", file=sys.stderr)
        sys.exit(1)

    init_db(days=config.history_days_to_keep)

    event_queue: queue.Queue = queue.Queue()
    paused = threading.Event()

    if config.pause_on_start:
        paused.set()

    hotkey_listener = HotkeyListener(config.hotkey, event_queue)
    hotkey_listener.start()

    mouse_listener = RightClickListener(event_queue)
    mouse_listener.start()

    tray_thread = threading.Thread(
        target=run_tray, args=(paused, event_queue), daemon=True
    )
    tray_thread.start()

    optimizer = Optimizer(config)

    print(f"PromptImprover running.")
    print(f"  Right-click anywhere to optimize (or press {config.hotkey} for the comparison view).")

    try:
        while True:
            try:
                event = event_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if event == "quit":
                break

            if event == "hotkey":
                if paused.is_set():
                    continue
                _handle_hotkey(config, optimizer)

            elif isinstance(event, tuple) and event[0] == "right_click":
                if paused.is_set():
                    continue
                _, x, y = event
                _handle_right_click(config, optimizer, x, y)

            elif event == "show_history":
                _show_history_window()

    finally:
        hotkey_listener.stop()
        mouse_listener.stop()
        print("PromptImprover stopped.")


def _run_optimization(config, optimizer, raw_text, app_ctx):
    """Shared optimization logic. Returns OptimizationResult or raises."""
    history_signal = None
    if config.learning_enabled:
        history_signal = get_history_signal(app_ctx.id, config, config.min_samples)

    return optimizer.optimize(
        raw_prompt=raw_text,
        app_context=app_ctx,
        persona_role=config.persona_role,
        persona_domain=config.persona_domain,
        persona_style=config.persona_style,
        history_signal=history_signal,
    )


def _handle_right_click(config, optimizer, cursor_x: int, cursor_y: int):
    """
    Right-click flow:
    1. Show a tiny non-focus-stealing 'Optimize' button near the cursor.
    2. If user clicks it, capture the full field, optimize, and inject back.
    3. No comparison overlay — fast, in-place replacement with an undo toast.
    """
    # Save the source window BEFORE showing any UI
    source_hwnd = get_active_hwnd()

    # Show the floating button — WS_EX_NOACTIVATE means source keeps focus
    clicked = show_optimize_button(cursor_x, cursor_y)
    if not clicked:
        return

    # Capture the field content (source window still has focus)
    raw_text = capture_field(target_hwnd=source_hwnd)
    if not raw_text.strip():
        _show_toast("Nothing to optimize — click into a text field first.")
        return

    app_ctx = detect()

    try:
        result = _run_optimization(config, optimizer, raw_text, app_ctx)
    except requests.exceptions.ConnectionError:
        _show_error_overlay("Ollama is not running.\n\nStart it with:\n  ollama serve")
        return
    except requests.exceptions.Timeout:
        _show_error_overlay(f"Optimization timed out ({config.timeout}s).\n\nTry a smaller model.")
        return
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            _show_error_overlay(
                f"Model '{config.model_name}' not found in Ollama.\n\n"
                f"Pull it first:\n  ollama pull {config.model_name}"
            )
        else:
            _show_error_overlay(f"LLM server error:\n{e}")
        return
    except Exception as e:
        _show_error_overlay(f"Unexpected error:\n{e}")
        return

    # Inject directly — no overlay, source window gets the optimized text
    inject(result.optimized_text, target_hwnd=source_hwnd)
    _show_toast("✓ Optimized  —  Ctrl+Z to undo")

    if config.learning_enabled:
        record(OptRecord(
            app_context=app_ctx.id,
            raw_prompt=raw_text,
            opt_prompt=result.optimized_text,
            action="accepted",
            final_text=result.optimized_text,
            model=result.model,
            latency_ms=result.latency_ms,
        ))


def _handle_hotkey(config, optimizer):
    """
    Hotkey flow (Ctrl+Shift+.):
    Shows the full comparison overlay so the user can review before accepting.
    """
    source_hwnd = get_active_hwnd()
    raw_text = capture()

    if not raw_text.strip():
        _show_toast("Nothing to optimize — click into a text field first.")
        return

    app_ctx = detect()

    try:
        result = _run_optimization(config, optimizer, raw_text, app_ctx)
    except requests.exceptions.ConnectionError:
        _show_error_overlay("Ollama is not running.\n\nStart it with:\n  ollama serve")
        return
    except requests.exceptions.Timeout:
        _show_error_overlay(f"Optimization timed out ({config.timeout}s).\n\nTry a smaller model.")
        return
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            _show_error_overlay(
                f"Model '{config.model_name}' not found in Ollama.\n\n"
                f"Pull it first:\n  ollama pull {config.model_name}"
            )
        else:
            _show_error_overlay(f"LLM server error:\n{e}")
        return
    except Exception as e:
        _show_error_overlay(f"Unexpected error:\n{e}")
        return

    overlay_result = show_overlay(
        original=raw_text,
        optimized=result.optimized_text,
        app_context=app_ctx,
        model=result.model,
        latency_ms=result.latency_ms,
    )

    if overlay_result["action"] in ("accepted", "edited"):
        inject(overlay_result["text"], target_hwnd=source_hwnd)

    if config.learning_enabled:
        record(OptRecord(
            app_context=app_ctx.id,
            raw_prompt=raw_text,
            opt_prompt=result.optimized_text,
            action=overlay_result["action"],
            final_text=overlay_result.get("text"),
            model=result.model,
            latency_ms=result.latency_ms,
        ))


def _show_toast(msg: str):
    def _run():
        win = tk.Tk()
        win.title("PromptImprover")
        win.attributes("-topmost", True)
        win.configure(bg="#1e1e2e")
        win.resizable(False, False)
        win.overrideredirect(True)
        tk.Label(
            win, text=msg, bg="#1e1e2e", fg="#a6e3a1",
            font=("Segoe UI", 10), padx=16, pady=10,
        ).pack()
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        w = win.winfo_reqwidth()
        win.geometry(f"+{sw - w - 20}+60")
        win.after(3000, win.destroy)
        win.mainloop()

    threading.Thread(target=_run, daemon=True).start()


def _show_error_overlay(msg: str):
    def _run():
        win = tk.Tk()
        win.title("PromptImprover — Error")
        win.attributes("-topmost", True)
        win.configure(bg="#1e1e2e")
        win.resizable(True, False)
        tk.Label(
            win, text="⚠  " + msg, bg="#1e1e2e", fg="#f38ba8",
            font=("Segoe UI", 10), padx=24, pady=18, justify="left",
            wraplength=480,
        ).pack(fill="x")
        tk.Button(
            win, text="Dismiss", command=win.destroy,
            bg="#f38ba8", fg="#1e1e2e", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=12, pady=6,
        ).pack(pady=(0, 14))
        win.bind("<Escape>", lambda _: win.destroy())
        win.update_idletasks()
        w = max(win.winfo_reqwidth(), 420)
        h = win.winfo_reqheight()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 3}")
        win.mainloop()

    threading.Thread(target=_run, daemon=True).start()


def _show_history_window():
    from learning.db import get_connection

    def _run():
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT timestamp, app_context, action, latency_ms
                   FROM optimizations ORDER BY timestamp DESC LIMIT 100"""
            ).fetchall()

        win = tk.Tk()
        win.title("PromptImprover — History")
        win.attributes("-topmost", True)
        win.configure(bg="#1e1e2e")
        win.geometry("600x400")

        tk.Label(
            win, text="Optimization History (last 100)",
            bg="#1e1e2e", fg="#89b4fa",
            font=("Segoe UI", 11, "bold"), pady=8,
        ).pack()

        frame = tk.Frame(win, bg="#1e1e2e")
        frame.pack(fill="both", expand=True, padx=12, pady=8)

        sb = tk.Scrollbar(frame)
        sb.pack(side="right", fill="y")

        lb = tk.Listbox(
            frame, bg="#2a2a3e", fg="#cdd6f4",
            font=("Consolas", 9), relief="flat",
            yscrollcommand=sb.set, selectmode="browse",
        )
        lb.pack(fill="both", expand=True)
        sb.config(command=lb.yview)

        action_icons = {"accepted": "✓", "edited": "✎", "dismissed": "✗"}
        for r in rows:
            icon = action_icons.get(r["action"], "?")
            ms = f"{r['latency_ms']}ms" if r["latency_ms"] else "—"
            lb.insert("end", f"{r['timestamp'][:16]}  {icon}  {r['app_context']}  {ms}")

        win.mainloop()

    threading.Thread(target=_run, daemon=True).start()


if __name__ == "__main__":
    main()
