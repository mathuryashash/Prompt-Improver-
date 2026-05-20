# Architecture — PromptImprover

**Version:** 1.0  
**Last Updated:** 2026-05-19

---

## 1. System Overview

PromptImprover is a single-process Python application running as a Windows system tray app. It has no server component. All intelligence is delegated to a locally-running LLM (Ollama or LM Studio). Persistence is a single SQLite file.

```
┌─────────────────────────────────────────────────────────────┐
│                    PromptImprover Process                    │
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐ │
│  │    System    │   │    Hotkey    │   │   Overlay UI    │ │
│  │  Tray (UI)   │   │   Listener   │   │  (tkinter)      │ │
│  └──────┬───────┘   └──────┬───────┘   └────────┬────────┘ │
│         │                  │                     │          │
│         └──────────────────┼─────────────────────┘          │
│                            │ events                         │
│                    ┌───────▼────────┐                       │
│                    │  Orchestrator  │                       │
│                    │  (main.py)     │                       │
│                    └───────┬────────┘                       │
│          ┌─────────────────┼──────────────────┐             │
│          │                 │                  │             │
│  ┌───────▼──────┐ ┌────────▼──────┐ ┌────────▼──────────┐  │
│  │ App Detector │ │ Text Capture  │ │  Learning Engine  │  │
│  │              │ │               │ │  (SQLite)         │  │
│  └──────────────┘ └───────┬───────┘ └───────────────────┘  │
│                           │                                 │
│                   ┌───────▼───────┐                         │
│                   │   Optimizer   │                         │
│                   │  (meta-prompt │                         │
│                   │   assembly)   │                         │
│                   └───────┬───────┘                         │
└───────────────────────────┼─────────────────────────────────┘
                            │ HTTP POST (localhost only)
                   ┌────────▼────────┐
                   │  Ollama /       │
                   │  LM Studio      │
                   │  (local LLM)    │
                   └─────────────────┘
```

---

## 2. Component Responsibilities

### 2.1 Orchestrator (`main.py`)

The central coordinator. It:
- Initializes config, DB, and all modules at startup
- Registers hotkey callback with the listener
- On hotkey trigger: calls text capture → app detector → optimizer → opens overlay
- Passes overlay result (accept/edit/dismiss) to learning engine
- Handles graceful shutdown (releases keyboard hook, closes DB)

**Threading model:** The hotkey listener runs on a background thread (pynput requirement). Text capture, LLM call, and overlay all run on the main thread via a thread-safe queue. The overlay itself blocks the main thread until dismissed.

### 2.2 Hotkey Listener (`core/hotkey_listener.py`)

Wraps `pynput.keyboard.GlobalHotKeys`. Listens for the configured combination system-wide.

On trigger:
1. Puts an event on the main thread queue
2. Returns immediately (does not block the listener thread)

Key constraint: pynput's `GlobalHotKeys` must not block. All heavy work (LLM call, UI) happens on the main thread after the event is dequeued.

### 2.3 Text Capture (`core/text_capture.py`)

Extracts the current text from the active input field. Strategy:

```
1. Save current clipboard content
2. Send Ctrl+A (select all) to active window
3. Send Ctrl+C (copy)
4. Wait 100ms for clipboard to populate
5. Read clipboard text
6. Restore original clipboard content
7. Return captured text
```

Edge cases:
- If clipboard is empty after step 5 → return empty string (caller handles)
- If clipboard restore fails → log warning, continue (clipboard loss is non-fatal)
- Terminal emulators often use Ctrl+Shift+C for copy → detect terminal context and use that instead

Implementation uses `pyperclip` for clipboard and `pyautogui` or `pynput` for sending keystrokes.

### 2.4 App Detector (`core/app_detector.py`)

Queries the foreground window to determine which AI tool is active.

Detection logic (checked in order):

| Check | Condition | Context ID |
|---|---|---|
| Process name | `claude.exe` | `claude_desktop` |
| Process name | `chrome.exe` or `msedge.exe` AND window title contains "Claude" | `claude_web` |
| Process name | `opencode.exe` OR (terminal AND title contains "opencode") | `opencode` |
| Window title | contains "gemini" (case-insensitive) | `gemini_cli` |
| Process name | `hermes.exe` | `hermes` |
| Fallback | anything else | `generic` |

Uses `pywin32` (`win32gui`, `win32process`) to get foreground window handle → process ID → process name.

Returns a typed `AppContext` dataclass:
```python
@dataclass
class AppContext:
    id: str           # e.g. "claude_desktop"
    display_name: str # e.g. "Claude Desktop"
    icon: str         # emoji or path to icon file
    conventions: str  # human-readable style guide for this app
```

The `conventions` field is a short text block injected into the meta-prompt. Examples:

- `claude_desktop`: "Claude responds best to prompts with clear context, explicit output format requests, and examples where relevant. Be thorough."
- `gemini_cli`: "Gemini CLI expects concise, imperative commands. Avoid conversational preamble. One task per prompt."
- `opencode`: "OpenCode is a coding agent. Prompts should specify: language, task, constraints, and expected output shape."

### 2.5 Optimizer (`core/optimizer.py`)

Assembles the meta-prompt and calls the local LLM.

**Meta-prompt structure:**

```
SYSTEM:
You are an expert prompt engineer. Your job is to rewrite the user's rough prompt 
into a precise, effective prompt for the target AI tool. Return ONLY the rewritten 
prompt — no explanation, no preamble, no quotes.

USER PERSONA:
Role: {persona.role}
Domain: {persona.domain}
Preferred style: {persona.style}

TARGET APP: {app_context.display_name}
App conventions: {app_context.conventions}

LEARNING SIGNAL:
{history_signal or "Not enough history yet."}

RAW PROMPT TO OPTIMIZE:
{raw_prompt}

OPTIMIZED PROMPT:
```

**History signal** (populated after ≥5 samples):
A one-sentence behavioral pattern derived from acceptance data:
- "User tends to accept prompts that specify an explicit output format."
- "User often edits prompts to add language/framework constraints."

This is generated by `learning/profile.py` — it calls the LLM once on-demand to summarize the pattern from the last 20 interaction records. The summary is cached for 10 minutes.

**LLM call:**
- Ollama: `POST http://localhost:11434/api/generate` with `{"model": ..., "prompt": ..., "stream": false}`
- LM Studio: `POST http://localhost:1234/v1/completions` (OpenAI-compatible)
- Timeout: configurable (default 10s)
- Retry: 0 retries — timeout immediately shows error in overlay

### 2.6 Learning Engine (`learning/`)

Three files:

**`db.py`** — SQLite setup:
```sql
CREATE TABLE IF NOT EXISTS optimizations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    app_context TEXT NOT NULL,
    raw_prompt  TEXT,
    opt_prompt  TEXT,
    action      TEXT NOT NULL,  -- 'accepted' | 'edited' | 'dismissed'
    final_text  TEXT,           -- what was actually injected (if accepted/edited)
    model       TEXT,
    latency_ms  INTEGER
);

CREATE TABLE IF NOT EXISTS persona_cache (
    app_context TEXT PRIMARY KEY,
    summary     TEXT,
    updated_at  TEXT
);
```

Auto-prune: on startup, delete rows older than 90 days.

**`history.py`** — write and query operations:
- `record(optimization_result)` — insert one row
- `get_recent(app_context, limit=20)` — fetch recent rows for a given app
- `acceptance_rate(app_context)` — float 0.0–1.0
- `has_enough_samples(app_context, min=5)` — bool

**`profile.py`** — persona and pattern summarization:
- Reads persona from `config.toml`
- `get_history_signal(app_context)` → calls LLM to summarize recent history into one sentence (cached 10min in `persona_cache` table)

### 2.7 Overlay UI (`ui/overlay.py`)

A `tkinter.Toplevel` window created fresh for each optimization:

```
┌─────────────────────────────────────────────┐
│  🤖 Claude Desktop  ·  mistral  ·  1.3s     │
├─────────────────────────────────────────────┤
│  ORIGINAL                                   │
│  ┌─────────────────────────────────────┐    │
│  │ make a function that sorts          │    │
│  └─────────────────────────────────────┘    │
│  OPTIMIZED                                  │
│  ┌─────────────────────────────────────┐    │
│  │ Write a Python function that sorts  │    │
│  │ a list of dicts by key 'timestamp'  │    │
│  │ in descending order, handling None  │    │
│  │ values safely. Include type hints   │    │
│  │ and a docstring.                    │    │
│  └─────────────────────────────────────┘    │
├─────────────────────────────────────────────┤
│   [Accept ↵]    [Edit Ctrl+E]   [Dismiss ⎋] │
└─────────────────────────────────────────────┘
```

Behaviour:
- `always_on_top=True`, positioned near active window
- Auto-dismisses after 30s of no interaction (countdown shown in title bar)
- Returns a result dict: `{"action": "accepted"|"edited"|"dismissed", "text": str}`

### 2.8 System Tray (`ui/tray.py`)

Uses `pystray` with a custom icon (generated via Pillow if no icon file present).

Menu items:
- **PromptImprover** (disabled, header)
- **Enabled** (checkable) — toggles hotkey interception
- **Separator**
- **Edit Persona** — opens `config.toml` in default editor
- **View History** — opens a simple tkinter list window
- **Settings** — opens config.toml in default editor
- **Separator**
- **Quit**

---

## 3. Data Flow — Full Hotkey Cycle

```
1. [pynput thread] hotkey pressed
      → queue.put(HotkeyEvent())

2. [main thread] event loop dequeues HotkeyEvent
      → if overlay already open: ignore
      → if paused: ignore

3. text_capture.capture()
      → saves clipboard
      → sends Ctrl+A + Ctrl+C
      → reads new clipboard
      → restores clipboard
      → returns raw_text (or "" if empty)

4. if raw_text == "": show toast "nothing to optimize" → stop

5. app_detector.detect()
      → win32gui.GetForegroundWindow()
      → process name lookup
      → returns AppContext

6. profile.get_persona()
      → reads config.toml persona section

7. history.get_history_signal(app_context)
      → if <5 samples: returns None
      → else: returns cached summary or calls LLM to generate one

8. optimizer.optimize(raw_text, app_context, persona, history_signal)
      → assembles meta-prompt
      → POST to Ollama/LM Studio
      → returns optimized_text (or raises TimeoutError / ConnectionError)

9. overlay.show(raw_text, optimized_text, app_context)
      → blocks until user action
      → returns OverlayResult

10. if result.action in ("accepted", "edited"):
       text_capture.inject(result.text)
          → write to clipboard
          → send Ctrl+A + Ctrl+V to active window

11. history.record(OverlayResult, app_context, model, latency)
```

---

## 4. SQLite Schema

```sql
-- All prompt optimization events
CREATE TABLE optimizations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL DEFAULT (datetime('now')),
    app_context TEXT    NOT NULL,
    raw_prompt  TEXT,
    opt_prompt  TEXT,
    action      TEXT    NOT NULL CHECK(action IN ('accepted','edited','dismissed')),
    final_text  TEXT,
    model       TEXT,
    latency_ms  INTEGER
);

-- Cached per-app learning summaries (LLM-generated, refreshed every 10 min)
CREATE TABLE persona_cache (
    app_context TEXT    PRIMARY KEY,
    summary     TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_opt_app_ts ON optimizations(app_context, timestamp);
```

---

## 5. Threading Model

```
Main Thread
├── tkinter event loop (overlay + tray run here)
├── Dequeues hotkey events
├── Runs capture, detect, optimize (blocking but short-lived)
└── Shows overlay (blocks until dismissed)

Background Thread (pynput)
└── Listens for global hotkey
    └── puts event on thread-safe Queue

Background Thread (pystray)
└── Runs system tray event loop
    └── Menu callbacks dispatch to main thread queue
```

Key rule: **tkinter must only be called from the main thread.** All hotkey events go through a `queue.Queue`, never calling tkinter directly from the pynput thread.

---

## 6. Error Handling Matrix

| Error | Detection | User-facing behaviour |
|---|---|---|
| Ollama not running | `ConnectionRefusedError` on POST | Overlay: "Ollama is not running. Start it with `ollama serve`." |
| LLM timeout | `requests.Timeout` | Overlay: "Optimization timed out (10s). Try a smaller model." |
| Empty text capture | Empty string returned | Toast notification: "Nothing captured — click into a text field." |
| Config parse error | `toml.TOMLDecodeError` on startup | Print to stderr + exit with message pointing to config file |
| SQLite write error | Exception in `history.record` | Log warning, continue — history failure must not block the optimization flow |
| Clipboard restore fail | Exception in `text_capture` | Log warning, continue — user clipboard may be lost but app stays running |

---

## 7. Key Dependencies

| Library | Purpose | Version |
|---|---|---|
| `pynput` | Global keyboard hook | ^1.7 |
| `pywin32` | Win32 API (foreground window, process name) | ^306 |
| `pyperclip` | Cross-platform clipboard read/write | ^1.8 |
| `pyautogui` | Sending keystrokes (Ctrl+A, Ctrl+C, Ctrl+V) | ^0.9 |
| `requests` | HTTP calls to Ollama / LM Studio | ^2.31 |
| `pystray` | System tray icon | ^0.19 |
| `Pillow` | Icon image generation for tray | ^10.0 |
| `tomllib` / `tomli` | TOML config parsing (stdlib in 3.11+) | stdlib |
| `tkinter` | Overlay UI | stdlib |
| `sqlite3` | Prompt history DB | stdlib |

---

## 8. Security Considerations

- **No network egress.** All HTTP calls target `localhost`. No DNS resolution, no external IPs.
- **Clipboard contents are transient.** Original clipboard is always restored, even on error.
- **SQLite is local only.** No shared memory, no named pipes, no IPC exposed to other processes.
- **Hotkey hook is read-only.** pynput's `GlobalHotKeys` does not suppress key events — it only listens. The hotkey itself still reaches the active application (this is intentional for Ctrl+Shift+P which has no default meaning in most apps).
