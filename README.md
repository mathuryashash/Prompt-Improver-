# PromptImprover

A Windows background application that intercepts any prompt you type — in Claude, OpenCode, Gemini CLI, Hermes, or any other AI tool — and rewrites it into a sharper, more effective version using a local LLM (Ollama / LM Studio).

Press a hotkey. Your raw thought becomes a precision-crafted prompt. No copy-paste, no context switching, no cloud data leakage.

---

## What It Does

You type a rough prompt in whichever AI tool you're using. When you're done, press **Ctrl+Shift+.** (configurable). PromptImprover:

1. Captures the text you just typed
2. Detects which application you're working in
3. Sends the prompt to a local LLM with a tailored meta-prompt that knows your persona, past behaviour, and the target app's conventions
4. Displays the rewritten prompt in a floating overlay
5. Lets you accept (replaces your original text), edit inline, or dismiss
6. Records your choice so future optimizations get smarter

Everything runs locally. No prompt leaves your machine.

---

## Key Features

| Feature | Description |
|---|---|
| **Universal capture** | Works in any Windows app — browser tabs, terminal emulators, native GUI apps |
| **App-aware optimization** | Knows Claude's conversational style differs from Gemini CLI's terse commands |
| **Local LLM backend** | Ollama or LM Studio — you pick the model |
| **Learning engine** | SQLite-backed history that tracks acceptance rate and adapts over time |
| **Persona memory** | Remembers your role, domain, and communication style across sessions |
| **Overlay UI** | Lightweight floating window — shows before/after diff, accept/edit/reject |
| **System tray** | Runs silently in background, right-click to configure or quit |
| **Configurable hotkey** | Default Ctrl+Shift+., fully remappable |

---

## Supported Target Apps (v1.0)

- **Claude** (claude.ai in Chrome/Edge, Claude Desktop)
- **OpenCode** (terminal-based)
- **Gemini CLI** (terminal-based)
- **Hermes** (detected by process name)
- **Generic fallback** — any other app gets sensible default optimization

---

## Prerequisites

| Requirement | Details |
|---|---|
| Windows 10/11 | 64-bit |
| Python 3.11+ | https://python.org |
| Ollama | https://ollama.com — install and pull at least one model (recommended: `mistral` or `llama3.1`) |
| (Optional) LM Studio | Alternative local model server at `http://localhost:1234` |

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/yourname/promptimprover
cd promptimprover

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Pull a local model (if using Ollama)
ollama pull mistral

# 5. Configure
copy config.example.toml config.toml
# Edit config.toml: set model, hotkey, persona

# 6. Run
python main.py
```

The app starts silently in the system tray. Open any AI tool, type a prompt, press **Ctrl+Shift+.**.

---

## Project Structure

```
promptimprover/
├── main.py                  # Entry point — boots tray, hooks, overlay
├── config.toml              # User configuration (hotkey, model, persona)
├── config.example.toml      # Template
├── requirements.txt
│
├── core/
│   ├── hotkey_listener.py   # Global keyboard hook (pynput)
│   ├── text_capture.py      # Clipboard-based text extraction
│   ├── app_detector.py      # Foreground window → app context
│   └── optimizer.py         # Calls local LLM to rewrite prompt
│
├── learning/
│   ├── db.py                # SQLite setup and migrations
│   ├── history.py           # Record and query prompt history
│   └── profile.py           # User persona and per-app preferences
│
├── ui/
│   ├── overlay.py           # Floating before/after window (tkinter)
│   └── tray.py              # System tray icon and menu (pystray)
│
└── docs/
    ├── README.md
    ├── PRD.md
    ├── ARCHITECTURE.md
    ├── IMPLEMENTATION.md
    └── ROADMAP.md
```

---

## Configuration (`config.toml`)

```toml
[app]
hotkey = "ctrl+shift+."
startup_with_windows = true

[model]
backend = "ollama"          # "ollama" | "lmstudio"
host = "http://localhost:11434"
model_name = "mistral"
timeout_seconds = 10

[persona]
role = "software developer"
domain = "backend systems, Python, distributed systems"
style = "concise, technical, no fluff"

[learning]
enabled = true
min_samples_before_adapting = 5
```

---

## Hotkey Flow

```
User types prompt in any app
         │
   Ctrl+Shift+. pressed
         │
   Text captured from active field (clipboard trick)
         │
   App context detected (window title + process name)
         │
   Meta-prompt assembled:
     [persona] + [app conventions] + [history signal] + [raw prompt]
         │
   Local LLM called (Ollama / LM Studio)
         │
   Overlay appears with:
     ┌─ Original prompt ─────────────────┐
     │  "make a function that sorts"     │
     ├─ Optimized prompt ────────────────┤
     │  "Write a Python function that    │
     │   sorts a list of dicts by key    │
     │   'timestamp' in descending order │
     │   and handles None values safely."│
     └───────────────────────────────────┘
       [Accept]   [Edit]   [Dismiss]
         │
   Choice recorded in SQLite
         │
   If accepted: text replaces original via clipboard injection
```

---

## Docs Index

- [PRD.md](PRD.md) — Full product requirements and user stories
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design, data flow, component responsibilities
- [IMPLEMENTATION.md](IMPLEMENTATION.md) — Developer guide, code patterns, Ollama integration
- [ROADMAP.md](ROADMAP.md) — Phased build plan with milestones
