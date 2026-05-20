# Implementation Guide — PromptImprover

**Version:** 1.0  
**Last Updated:** 2026-05-19

This document is the developer reference. It covers: project setup, module-by-module implementation notes, key code patterns, the Ollama integration, and the meta-prompt design.

---

## 1. Environment Setup

### 1.1 Python version

Use Python 3.11+. The `tomllib` module (TOML parsing) is stdlib from 3.11 onwards.

```bash
python --version   # must be 3.11+
```

### 1.2 Virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 1.3 requirements.txt

```
pynput==1.7.6
pywin32==306
pyperclip==1.8.2
pyautogui==0.9.54
requests==2.31.0
pystray==0.19.5
Pillow==10.3.0
```

### 1.4 Ollama setup

```bash
# Install from https://ollama.com
# Then pull a model:
ollama pull mistral          # recommended: good quality, fast on CPU
ollama pull llama3.1         # alternative: stronger reasoning
ollama pull phi3:mini        # lightweight option for slow machines

# Verify it's running:
ollama serve                 # starts server on :11434
curl http://localhost:11434/api/tags   # should list your models
```

---

## 2. Project Scaffold

Create this structure before writing any code:

```bash
mkdir -p promptimprover/{core,learning,ui,assets}
touch promptimprover/main.py
touch promptimprover/config.example.toml
touch promptimprover/requirements.txt
touch promptimprover/core/{__init__,hotkey_listener,text_capture,app_detector,optimizer}.py
touch promptimprover/learning/{__init__,db,history,profile}.py
touch promptimprover/ui/{__init__,overlay,tray}.py
```

---

## 3. Configuration (`config.example.toml`)

```toml
[app]
hotkey = "ctrl+shift+p"
startup_with_windows = false
pause_on_start = false

[model]
backend = "ollama"           # "ollama" | "lmstudio"
host = "http://localhost:11434"
model_name = "mistral"
timeout_seconds = 10

[persona]
role = "software developer"
domain = "Python, backend systems, APIs"
style = "concise and technical, avoid filler words"

[learning]
enabled = true
min_samples_before_adapting = 5
history_days_to_keep = 90
```

Loading config in Python:

```python
# core/config.py
import tomllib
from pathlib import Path
from dataclasses import dataclass

CONFIG_PATH = Path(__file__).parent.parent / "config.toml"

@dataclass
class Config:
    hotkey: str
    backend: str
    host: str
    model_name: str
    timeout: int
    persona_role: str
    persona_domain: str
    persona_style: str
    learning_enabled: bool
    min_samples: int

def load_config() -> Config:
    with open(CONFIG_PATH, "rb") as f:
        raw = tomllib.load(f)
    return Config(
        hotkey=raw["app"]["hotkey"],
        backend=raw["model"]["backend"],
        host=raw["model"]["host"],
        model_name=raw["model"]["model_name"],
        timeout=raw["model"]["timeout_seconds"],
        persona_role=raw["persona"]["role"],
        persona_domain=raw["persona"]["domain"],
        persona_style=raw["persona"]["style"],
        learning_enabled=raw["learning"]["enabled"],
        min_samples=raw["learning"]["min_samples_before_adapting"],
    )
```

---

## 4. Module Implementation

### 4.1 Hotkey Listener (`core/hotkey_listener.py`)

```python
import queue
import threading
from pynput import keyboard

class HotkeyListener:
    def __init__(self, hotkey_str: str, event_queue: queue.Queue):
        """
        hotkey_str: e.g. "ctrl+shift+p"
        event_queue: thread-safe queue — puts True on hotkey press
        """
        self._queue = event_queue
        self._hotkey_str = self._parse(hotkey_str)
        self._listener = None

    def _parse(self, s: str) -> str:
        # pynput format: "<ctrl>+<shift>+p"
        parts = s.split("+")
        def fmt(p):
            p = p.strip().lower()
            return f"<{p}>" if p in ("ctrl","shift","alt","cmd","win") else p
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
```

### 4.2 App Detector (`core/app_detector.py`)

```python
import win32gui
import win32process
import psutil
from dataclasses import dataclass

APP_CONVENTIONS = {
    "claude_desktop": (
        "Claude Desktop works best with rich, context-heavy prompts. "
        "Specify role, task, output format, and constraints explicitly. "
        "Claude handles multi-step reasoning well — break complex asks into subtasks."
    ),
    "claude_web": (
        "Same as Claude Desktop. Conversational tone is fine but precision helps. "
        "Specify output format (markdown, JSON, plain text) explicitly."
    ),
    "opencode": (
        "OpenCode is a terminal coding agent. Be specific about: programming language, "
        "framework version, what already exists, what needs to change, and expected output. "
        "Reference file paths and function names when relevant."
    ),
    "gemini_cli": (
        "Gemini CLI expects concise, imperative prompts. One task per prompt. "
        "Avoid conversational preamble. Use technical terms directly."
    ),
    "hermes": (
        "Hermes is a local LLM interface. Be explicit about output format. "
        "Shorter prompts often work better. Specify exactly what you want returned."
    ),
    "generic": (
        "Write a clear, specific prompt. Include: what you want done, any constraints, "
        "and what the output should look like."
    ),
}

DISPLAY_NAMES = {
    "claude_desktop": "Claude Desktop",
    "claude_web": "Claude (Web)",
    "opencode": "OpenCode",
    "gemini_cli": "Gemini CLI",
    "hermes": "Hermes",
    "generic": "Generic App",
}

ICONS = {
    "claude_desktop": "🤖",
    "claude_web": "🌐",
    "opencode": "💻",
    "gemini_cli": "✨",
    "hermes": "🔮",
    "generic": "⚡",
}

@dataclass
class AppContext:
    id: str
    display_name: str
    icon: str
    conventions: str

def detect() -> AppContext:
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd).lower()

    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        proc_name = ""

    ctx_id = _classify(proc_name, title)
    return AppContext(
        id=ctx_id,
        display_name=DISPLAY_NAMES[ctx_id],
        icon=ICONS[ctx_id],
        conventions=APP_CONVENTIONS[ctx_id],
    )

def _classify(proc_name: str, title: str) -> str:
    if "claude" in proc_name and "chrome" not in proc_name and "edge" not in proc_name:
        return "claude_desktop"
    if ("chrome" in proc_name or "msedge" in proc_name) and "claude" in title:
        return "claude_web"
    if "opencode" in proc_name or "opencode" in title:
        return "opencode"
    if "gemini" in title or "gemini" in proc_name:
        return "gemini_cli"
    if "hermes" in proc_name:
        return "hermes"
    return "generic"
```

### 4.3 Text Capture (`core/text_capture.py`)

```python
import time
import pyperclip
import pyautogui

def capture() -> str:
    """
    Captures text from the active input field.
    Returns the captured text, or "" if nothing was captured.
    Restores the original clipboard content.
    """
    original_clipboard = _safe_get_clipboard()

    try:
        # Select all and copy
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.1)   # wait for clipboard to populate

        captured = _safe_get_clipboard()
    finally:
        _safe_set_clipboard(original_clipboard)

    return captured if captured else ""

def inject(text: str):
    """
    Replaces the active field's content with text.
    Strategy: write to clipboard → select all → paste.
    """
    original_clipboard = _safe_get_clipboard()
    try:
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
    finally:
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
        pass  # non-fatal
```

**Terminal emulator note:** In terminals, `Ctrl+A` moves to start-of-line (bash). To select all text in a terminal, you typically need `Ctrl+Shift+A` or rely on the user pre-selecting. Document this limitation in v1.0 and add terminal-specific handling in v1.1.

### 4.4 Optimizer (`core/optimizer.py`)

```python
import requests
from dataclasses import dataclass
from core.app_detector import AppContext

@dataclass
class OptimizationResult:
    optimized_text: str
    model: str
    latency_ms: int

class Optimizer:
    def __init__(self, config):
        self.config = config

    def optimize(
        self,
        raw_prompt: str,
        app_context: AppContext,
        persona_role: str,
        persona_domain: str,
        persona_style: str,
        history_signal: str | None = None,
    ) -> OptimizationResult:
        meta_prompt = self._build_meta_prompt(
            raw_prompt, app_context, persona_role,
            persona_domain, persona_style, history_signal
        )

        import time
        start = time.time()
        optimized = self._call_llm(meta_prompt)
        latency_ms = int((time.time() - start) * 1000)

        return OptimizationResult(
            optimized_text=optimized.strip(),
            model=self.config.model_name,
            latency_ms=latency_ms,
        )

    def _build_meta_prompt(self, raw, ctx, role, domain, style, signal) -> str:
        history_block = (
            f"LEARNING SIGNAL (based on your past behaviour):\n{signal}\n"
            if signal else
            "LEARNING SIGNAL: Not enough history yet — using defaults.\n"
        )

        return f"""You are an expert prompt engineer. Rewrite the raw prompt below into a precise, \
effective prompt for the target AI tool. Return ONLY the rewritten prompt — no explanation, \
no preamble, no surrounding quotes.

USER PERSONA:
- Role: {role}
- Domain expertise: {domain}
- Preferred output style: {style}

TARGET APP: {ctx.display_name}
App conventions: {ctx.conventions}

{history_block}
RAW PROMPT TO OPTIMIZE:
{raw}

OPTIMIZED PROMPT:"""

    def _call_llm(self, prompt: str) -> str:
        cfg = self.config
        timeout = cfg.timeout

        if cfg.backend == "ollama":
            url = f"{cfg.host}/api/generate"
            payload = {
                "model": cfg.model_name,
                "prompt": prompt,
                "stream": False,
            }
            resp = requests.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            return resp.json()["response"]

        elif cfg.backend == "lmstudio":
            url = f"{cfg.host}/v1/completions"
            payload = {
                "model": cfg.model_name,
                "prompt": prompt,
                "max_tokens": 500,
                "temperature": 0.3,
                "stop": ["\n\n"],
            }
            resp = requests.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            return resp.json()["choices"][0]["text"]

        else:
            raise ValueError(f"Unknown backend: {cfg.backend}")
```

### 4.5 Learning Engine (`learning/db.py`, `history.py`, `profile.py`)

**`learning/db.py`**

```python
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "history.db"

def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS optimizations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT    NOT NULL DEFAULT (datetime('now')),
                app_context TEXT    NOT NULL,
                raw_prompt  TEXT,
                opt_prompt  TEXT,
                action      TEXT    NOT NULL,
                final_text  TEXT,
                model       TEXT,
                latency_ms  INTEGER
            );

            CREATE TABLE IF NOT EXISTS persona_cache (
                app_context TEXT    PRIMARY KEY,
                summary     TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_opt_app_ts
                ON optimizations(app_context, timestamp);
        """)
        # Prune old entries
        conn.execute(
            "DELETE FROM optimizations WHERE timestamp < datetime('now', '-90 days')"
        )
```

**`learning/history.py`**

```python
from dataclasses import dataclass
from learning.db import get_connection

@dataclass
class OptRecord:
    app_context: str
    raw_prompt: str
    opt_prompt: str
    action: str          # 'accepted' | 'edited' | 'dismissed'
    final_text: str | None
    model: str
    latency_ms: int

def record(r: OptRecord):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO optimizations
               (app_context, raw_prompt, opt_prompt, action, final_text, model, latency_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (r.app_context, r.raw_prompt, r.opt_prompt,
             r.action, r.final_text, r.model, r.latency_ms)
        )

def get_recent(app_context: str, limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT action, opt_prompt, final_text FROM optimizations
               WHERE app_context = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (app_context, limit)
        ).fetchall()
    return [dict(r) for r in rows]

def has_enough_samples(app_context: str, min_count: int = 5) -> bool:
    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM optimizations WHERE app_context = ?",
            (app_context,)
        ).fetchone()[0]
    return count >= min_count

def acceptance_rate(app_context: str) -> float:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT
                COUNT(*) as total,
                SUM(CASE WHEN action IN ('accepted','edited') THEN 1 ELSE 0 END) as accepted
               FROM optimizations WHERE app_context = ?""",
            (app_context,)
        ).fetchone()
    if not row or row["total"] == 0:
        return 0.0
    return row["accepted"] / row["total"]
```

**`learning/profile.py`**

```python
import json
import time
import requests
from learning.history import get_recent, has_enough_samples
from learning.db import get_connection

CACHE_TTL_SECONDS = 600  # 10 minutes

def get_history_signal(app_context: str, config, min_samples: int = 5) -> str | None:
    if not has_enough_samples(app_context, min_samples):
        return None

    # Check cache
    cached = _get_cached_summary(app_context)
    if cached:
        return cached

    # Generate summary from recent history
    recent = get_recent(app_context, limit=20)
    summary = _generate_summary(recent, app_context, config)

    _cache_summary(app_context, summary)
    return summary

def _generate_summary(records: list[dict], app_context: str, config) -> str:
    accepted = [r for r in records if r["action"] in ("accepted", "edited")]
    dismissed = [r for r in records if r["action"] == "dismissed"]

    prompt = f"""You are analyzing how a user interacts with an AI prompt optimizer in {app_context}.

Recent optimization history (last {len(records)} interactions):
- Accepted/Edited: {len(accepted)} times
- Dismissed: {len(dismissed)} times

Sample accepted prompts (what the user liked):
{json.dumps([r['opt_prompt'][:200] for r in accepted[:5]], indent=2)}

Sample dismissed prompts (what the user rejected):
{json.dumps([r['opt_prompt'][:200] for r in dismissed[:3]], indent=2)}

In ONE sentence, describe what kinds of optimizations this user tends to accept vs. reject.
Be specific and actionable. Example: "User tends to accept prompts that specify output format
and reject ones that add unnecessary verbosity."

Summary:"""

    try:
        if config.backend == "ollama":
            resp = requests.post(
                f"{config.host}/api/generate",
                json={"model": config.model_name, "prompt": prompt, "stream": False},
                timeout=config.timeout
            )
            return resp.json()["response"].strip()
    except Exception:
        pass

    return f"User has accepted {len(accepted)} of {len(records)} optimizations in {app_context}."

def _get_cached_summary(app_context: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT summary, updated_at FROM persona_cache WHERE app_context = ?""",
            (app_context,)
        ).fetchone()
    if not row:
        return None
    # Check TTL
    import datetime
    updated = datetime.datetime.fromisoformat(row["updated_at"])
    age = (datetime.datetime.utcnow() - updated).total_seconds()
    if age > CACHE_TTL_SECONDS:
        return None
    return row["summary"]

def _cache_summary(app_context: str, summary: str):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO persona_cache(app_context, summary)
               VALUES (?, ?)
               ON CONFLICT(app_context) DO UPDATE SET summary=excluded.summary,
               updated_at=datetime('now')""",
            (app_context, summary)
        )
```

### 4.6 Main Orchestrator (`main.py`)

```python
import queue
import threading
import time
import requests.exceptions
from core.config import load_config
from core.hotkey_listener import HotkeyListener
from core.text_capture import capture, inject
from core.app_detector import detect
from core.optimizer import Optimizer
from learning.db import init_db
from learning.history import record, OptRecord
from learning.profile import get_history_signal
from ui.overlay import show_overlay
from ui.tray import run_tray

def main():
    config = load_config()
    init_db()

    event_queue = queue.Queue()
    paused = threading.Event()   # set = paused

    listener = HotkeyListener(config.hotkey, event_queue)
    listener.start()

    # Run tray in background thread
    tray_thread = threading.Thread(
        target=run_tray, args=(paused, event_queue), daemon=True
    )
    tray_thread.start()

    optimizer = Optimizer(config)

    print("PromptImprover running. Press", config.hotkey, "to optimize a prompt.")

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

    finally:
        listener.stop()

def _handle_hotkey(config, optimizer):
    raw_text = capture()

    if not raw_text.strip():
        _show_toast("Nothing to optimize — click into a text field first.")
        return

    app_ctx = detect()
    history_signal = get_history_signal(app_ctx.id, config, config.min_samples)

    try:
        result = optimizer.optimize(
            raw_prompt=raw_text,
            app_context=app_ctx,
            persona_role=config.persona_role,
            persona_domain=config.persona_domain,
            persona_style=config.persona_style,
            history_signal=history_signal,
        )
    except requests.exceptions.ConnectionError:
        _show_error("Ollama is not running.\nStart it with: ollama serve")
        return
    except requests.exceptions.Timeout:
        _show_error(f"Optimization timed out ({config.timeout}s).\nTry a smaller model.")
        return

    overlay_result = show_overlay(
        original=raw_text,
        optimized=result.optimized_text,
        app_context=app_ctx,
        model=result.model,
        latency_ms=result.latency_ms,
    )

    if overlay_result["action"] in ("accepted", "edited"):
        inject(overlay_result["text"])

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
    # Use tray notification or a brief tkinter popup
    print("[TOAST]", msg)  # replace with actual toast in UI implementation

def _show_error(msg: str):
    print("[ERROR]", msg)  # replace with overlay error display

if __name__ == "__main__":
    main()
```

---

## 5. Meta-Prompt Design Principles

The meta-prompt is the heart of the system. Keep these rules when modifying it:

1. **Output-only instruction.** Always say "Return ONLY the rewritten prompt." Without this, models add explanations.

2. **App conventions are short (2-3 sentences).** Don't dump a style guide — give the model just enough to adjust tone.

3. **Persona before conventions.** The LLM should know who the user is before it knows where they're writing.

4. **History signal is one sentence.** More than one sentence causes the model to over-fit to past behaviour.

5. **No examples in the meta-prompt.** Few-shot examples increase latency significantly on local models. Trust the instruction.

6. **Temperature 0.3–0.5.** Low enough to be consistent, high enough to avoid robotic output.

---

## 6. Startup with Windows

To launch PromptImprover automatically on login, add a registry entry:

```python
# ui/tray.py — called from "Start with Windows" menu toggle
import winreg

APP_NAME = "PromptImprover"
APP_PATH = str(Path(__file__).parent.parent / "main.py")

def enable_startup():
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE
    )
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'pythonw "{APP_PATH}"')
    winreg.CloseKey(key)

def disable_startup():
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE
    )
    try:
        winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
    winreg.CloseKey(key)
```

Note: Use `pythonw.exe` (not `python.exe`) to suppress the console window on startup.

---

## 7. Common Pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| Calling tkinter from pynput thread | Crash or frozen overlay | Always use Queue — never call tkinter from the hotkey callback |
| `Ctrl+A` in terminal moves cursor, not selects | Empty capture in terminal | Detect terminal context and use `Ctrl+Shift+A` or prompt user to select manually |
| Clipboard race condition | Captured text is from previous clipboard | Increase sleep after `Ctrl+C` from 100ms to 150ms |
| Ollama model not found | `404` from Ollama API | Validate model exists at startup: `GET /api/tags` and check names |
| pynput conflicts with admin apps | Hotkey doesn't fire in Task Manager, UAC dialogs | Expected — pynput cannot hook into elevated processes without running as admin |
| tkinter overlay flickers | Overlay appears then disappears | Set `overlay.update()` before `overlay.mainloop()` |
