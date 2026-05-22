<div align="center">

<h1>⚡ PromptImprover</h1>

<p><strong>A local-first, AI-powered prompt optimizer that lives in your Windows system tray.</strong><br>
Rewrite any text in any application — instantly, privately, and entirely on-device.</p>

<p>
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-0078D4?style=for-the-badge&logo=windows" alt="Platform">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/backend-Ollama%20%7C%20LM%20Studio-FF6B35?style=for-the-badge" alt="Backend">
  <img src="https://img.shields.io/badge/license-MIT-22C55E?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/privacy-100%25%20local-8B5CF6?style=for-the-badge" alt="Privacy">
</p>

</div>

---

## What is PromptImprover?

PromptImprover is a **Windows system-tray utility** that silently watches your keyboard and mouse. When you right-click in any text field, a small **⚡ Optimize** button appears. One click sends your text to a **locally running LLM** (via Ollama or LM Studio), rewrites it, and places the result back in your clipboard — all without leaving your current application.

> **Zero cloud. Zero API keys. Zero subscriptions. Your text never leaves your machine.**

It is designed for developers, researchers, writers, and power users who type prompts and instructions all day and want them to be precise, clear, and well-structured — without breaking their flow.

---

## Screenshots

| Right-click any text field | Comparison overlay | System tray |
|:---:|:---:|:---:|
| A non-intrusive ⚡ Optimize button appears | Side-by-side diff with Accept / Edit / Dismiss | Lightweight — always there, never in the way |

---

## Features

### Core
- **Right-click to optimize** — works in any Windows application (VS Code, browsers, terminals, Word, Slack, etc.)
- **Ctrl+Shift+.** — opens a full comparison overlay with the original and rewritten text side-by-side
- **Adaptive learning** — tracks your accept/reject history and adjusts the rewrite style over time
- **App-aware rewrites** — detects the foreground application and tailors the output style accordingly (code editor vs. chat app vs. document)

### Privacy & Performance
- **100% local** — all inference runs on your machine via Ollama or LM Studio
- **No telemetry, no accounts, no cloud** — your prompts are never transmitted anywhere
- **Lightweight** — ~15 MB install, negligible CPU/RAM when idle

### UX
- **Single-instance enforcement** — double-launching shows a notification instead of creating a duplicate tray icon
- **No console window** — double-click `run.pyw` or the Desktop shortcut; nothing appears except the tray icon
- **Auto-dismiss overlay** — 30-second countdown with mouse/keyboard reset
- **Non-focus-stealing UI** — the Optimize button and loading spinner appear without stealing focus from your active window, so your text selection is preserved
- **Customizable persona** — configure your role, domain, and preferred writing style in `config.toml`

---

## Architecture

```
promptimprover/
│
├── main.py                   # Entry point: event loop, orchestrates all components
├── run.pyw                   # No-console launcher (double-click this)
├── Create Shortcut.ps1       # One-time script to create a Desktop shortcut
│
├── core/
│   ├── config.py             # TOML config loader with defaults
│   ├── hotkey_listener.py    # Win32 WH_KEYBOARD_LL hook (pure ctypes, no pynput)
│   ├── mouse_listener.py     # Win32 WH_MOUSE_LL hook  (pure ctypes, no pynput)
│   ├── app_detector.py       # Detects foreground application type
│   ├── optimizer.py          # Builds LLM message chain, calls backend
│   ├── text_capture.py       # Clipboard capture and injection via Win32
│   └── paths.py              # Cross-platform path helpers
│
├── ui/
│   ├── overlay.py            # Comparison overlay (Tkinter, dark theme)
│   ├── context_menu.py       # ⚡ Optimize popup + loading spinner
│   └── tray.py               # pystray system-tray icon and menu
│
├── learning/
│   ├── db.py                 # SQLite schema and migrations
│   ├── history.py            # Record accept/reject decisions
│   └── profile.py            # Compute history signal for adaptive prompting
│
├── prompt_templates/
│   └── meta_prompt.json      # LLM system prompt and instruction templates
│
├── config.example.toml       # Documented config template — copy to config.toml
├── requirements.txt          # Python dependencies
└── test_*.py                 # Test suites (hooks, system, single-instance)
```

### How a right-click optimization works

```
Right-click detected (WH_MOUSE_LL)
        │
        ▼
⚡ Optimize button shown (non-focus-stealing Tkinter popup)
        │
        ▼
User clicks Optimize → text captured from clipboard (Win32 SendKeys Ctrl+C)
        │
        ▼
AppContext detected (foreground window title / class)
        │
        ▼
History signal computed (past accept/reject ratio)
        │
        ▼
LLM message chain built (system prompt + persona + app context + signal)
        │
        ▼
Request sent to Ollama / LM Studio  →  optimized text returned
        │
        ▼
Optimized text injected into clipboard + toast notification shown
        │
        ▼
User presses Ctrl+V to paste (or uses the Ctrl+Shift+. overlay to review first)
```

---

## Requirements

| Component | Minimum |
|---|---|
| **OS** | Windows 10 / 11 (x64) |
| **Python** | 3.11 or higher (3.13 recommended) |
| **LLM Backend** | [Ollama](https://ollama.com) **or** [LM Studio](https://lmstudio.ai) |
| **RAM** | 8 GB (16 GB recommended for 7B+ models) |
| **Disk** | ~15 MB for the app + model size (e.g. 2 GB for llama3.2:3b) |

---

## Installation

### 1. Install an LLM backend

**Option A — Ollama (recommended)**
```bash
# Download from https://ollama.com and install, then:
ollama pull llama3.2:3b
ollama serve          # starts on http://localhost:11434
```

**Option B — LM Studio**
Download from [lmstudio.ai](https://lmstudio.ai), load any GGUF model, and start the local server on `http://localhost:1234`.

---

### 2. Clone the repository

```bash
git clone https://github.com/mathuryashash/Prompt-Improver-.git
cd Prompt-Improver-
```

---

### 3. Create a virtual environment and install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

### 4. Configure

Copy the example config and edit it:

```bash
copy config.example.toml config.toml
notepad config.toml
```

Key settings to check:

```toml
[model]
backend    = "ollama"              # or "lmstudio"
host       = "http://localhost:11434"
model_name = "llama3.2:3b"        # change to whatever model you pulled

[persona]
role   = "software developer"
domain = "Python, backend systems, APIs"
style  = "concise and technical, avoid filler words"
```

---

### 5. Run the app

**Without a console window (recommended):**
```bash
.venv\Scripts\pythonw.exe run.pyw
```

**With a console (useful for debugging):**
```bash
.venv\Scripts\python.exe main.py
```

**Create a Desktop shortcut (run once):**
```powershell
powershell -ExecutionPolicy Bypass -File "Create Shortcut.ps1"
```
After this, double-click **PromptImprover** on your Desktop to launch with no terminal.

---

## Usage

### Right-click to optimize (inline)

1. Click into any text field in any application
2. Type your prompt / text
3. **Right-click** — a small ⚡ Optimize button appears near your cursor
4. Click it — a spinner shows while the LLM works
5. The optimized text is placed in your clipboard
6. **Ctrl+V** to paste

### Comparison overlay (Ctrl+Shift+.)

1. Type your prompt into any field
2. Press **Ctrl+Shift+.** anywhere
3. The overlay shows **ORIGINAL** vs **OPTIMIZED** side by side
4. Choose:
   - **Accept ↵** — copies optimized text to clipboard
   - **Edit** — make manual changes before accepting
   - **Dismiss Esc** — keep the original

### System tray menu

Right-click the tray icon for:
- **Enabled / Paused** toggle
- **Edit Persona / Settings** — opens `config.toml` in Notepad
- **View History** — see past optimizations
- **Quit**

---

## Configuration Reference

| Key | Type | Default | Description |
|---|---|---|---|
| `app.hotkey` | string | `"ctrl+shift+."` | Keyboard shortcut for the comparison overlay |
| `app.startup_with_windows` | bool | `true` | Add to Windows startup registry |
| `app.pause_on_start` | bool | `false` | Start in paused mode |
| `model.backend` | string | `"ollama"` | `"ollama"` or `"lmstudio"` |
| `model.host` | string | `"http://localhost:11434"` | Backend API base URL |
| `model.model_name` | string | `"llama3.2:3b"` | Model identifier |
| `model.timeout_seconds` | int | `30` | Request timeout |
| `model.temperature` | float | `0.4` | Creativity (0.0–1.0) |
| `persona.role` | string | `"software developer"` | Your professional role |
| `persona.domain` | string | `"Python, backend systems, APIs"` | Technologies / context |
| `persona.style` | string | `"concise and technical…"` | Preferred output style |
| `learning.enabled` | bool | `true` | Enable adaptive learning |
| `learning.min_samples_before_adapting` | int | `5` | Samples needed before adapting |
| `learning.history_days_to_keep` | int | `90` | SQLite retention period |

---

## Supported Models

PromptImprover works with any model served by Ollama or LM Studio. Recommended options:

| Model | Size | Speed | Best for |
|---|---|---|---|
| `llama3.2:3b` | 2 GB | Very fast | Daily use, quick rewrites |
| `llama3.2:latest` (8B) | 5 GB | Fast | Higher quality rewrites |
| `qwen2.5:7b` | 4 GB | Fast | Technical / code prompts |
| `mistral:latest` | 4 GB | Fast | General purpose |
| `qwen2.5-coder:7b` | 4 GB | Fast | Code-heavy prompts |

---

## Development

### Run the test suite

```bash
# All three suites
.venv\Scripts\python.exe test_single_instance.py
.venv\Scripts\python.exe test_hooks.py
.venv\Scripts\python.exe test_review.py
```

| Suite | What it tests |
|---|---|
| `test_single_instance.py` | Win32 mutex guard (prevents duplicate tray icons) |
| `test_hooks.py` | WH_KEYBOARD_LL and WH_MOUSE_LL hook installation, concurrency, clean shutdown |
| `test_review.py` | Config loading, DB, optimizer, clipboard, app detection, Ollama connectivity |

### Project conventions

- All Win32 input hooks use **pure `ctypes`** — no `pynput` dependency (incompatible with Python 3.13)
- Tkinter **must only run on the main thread** — all UI dispatch goes through `root.after()`
- The LLM is called in a **background daemon thread**; results are queued back to the main loop
- Persona and adaptive history signal are injected into every LLM request via `meta_prompt.json`

---

## Troubleshooting

### App doesn't appear in the tray
- Make sure Ollama/LM Studio is running before launching
- Check `config.toml` — `host` and `model_name` must match your backend
- Run `python main.py` (with console) and look for error output

### "Failed to install hook" error
- Ensure you are running with `pythonw.exe` or `python.exe` from the `.venv` (not a system Python)
- Low-level Win32 hooks require a proper desktop session — they won't work over SSH or in headless environments

### Duplicate tray icon
- The single-instance guard (Win32 named mutex) prevents this automatically
- If you see two icons, quit both via the tray menu and relaunch once

### Optimization is slow
- Switch to a smaller model (e.g. `llama3.2:3b` instead of an 8B model)
- Increase `timeout_seconds` if the model is large and your hardware is slower
- Ensure no other process is competing for GPU/CPU resources

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full planned feature list.

Highlights coming up:
- [ ] **Multi-backend support** — OpenAI-compatible API (OpenRouter, etc.)
- [ ] **Custom per-app personas** — different rewrites for Slack vs. VS Code vs. browser
- [ ] **Prompt history browser** — searchable UI to review and re-use past optimizations
- [ ] **PyInstaller `.exe` packaging** — true single-file executable, no Python required

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes with tests
4. Ensure all test suites pass
5. Open a pull request with a clear description

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <p>Built with Python, ctypes, Tkinter, pystray, and a locally running LLM.</p>
  <p><strong>Your prompts. Your machine. Your privacy.</strong></p>
</div>
