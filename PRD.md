# Product Requirements Document — PromptImprover

**Version:** 1.0  
**Status:** Draft  
**Author:** Yashash  
**Last Updated:** 2026-05-19

---

## 1. Problem Statement

AI tools like Claude, Gemini CLI, OpenCode, and Hermes are only as good as the prompts they receive. Most users, even experienced ones, write prompts that are:

- Too vague ("make this better")
- Missing context (no language, no constraints, no output format)
- Written for a human reader, not an LLM
- Not tuned to the specific model or interface they're targeting

The gap between what a user *means* and what they *type* is where 80% of poor AI output comes from. PromptImprover closes that gap in real-time, at the point of input, without breaking the user's flow.

---

## 2. Goals

| Goal | Metric |
|---|---|
| Improve prompt quality transparently | User accepts ≥ 60% of optimized prompts within 4 weeks |
| Zero friction in existing workflow | Activation time from hotkey to overlay < 2 seconds |
| Privacy-first | Zero prompts sent to external servers |
| Adaptable | Optimization quality improves measurably after 20+ interactions |

---

## 3. Non-Goals (v1.0)

- No browser extension (keyboard hook approach instead)
- No cloud sync of prompt history
- No multi-user support
- No prompt templating library (that's v2)
- No automatic background optimization (always user-triggered)

---

## 4. User Stories

### Core Flow

**US-001** — As a user typing a prompt in Claude, I want to press a hotkey and have my prompt automatically improved, so I don't have to manually rewrite it.

**US-002** — As a user, I want to see the original and optimized prompts side-by-side before accepting, so I stay in control of what gets sent.

**US-003** — As a user, I want to edit the optimized prompt before accepting it, so I can make final tweaks without starting over.

**US-004** — As a user, I want to dismiss the overlay without any changes, so I can choose when to use the optimization.

### App Awareness

**US-005** — As a user working in a terminal with Gemini CLI, I want the optimization to produce terse, instruction-style prompts appropriate for CLI tools, not conversational ones.

**US-006** — As a user working in Claude Desktop, I want the optimization to produce rich, context-heavy prompts suited to Claude's strengths.

**US-007** — As a user switching between apps, I want PromptImprover to detect which app I'm in automatically, without me configuring it each time.

### Learning & Personalization

**US-008** — As a user, I want the app to remember my role and domain so I don't have to re-explain my context in every prompt.

**US-009** — As a user, I want the system to learn from which optimizations I accept vs. reject, so suggestions improve over time.

**US-010** — As a user, I want to view and edit my persona profile (role, domain, style) from the system tray menu.

### Configuration

**US-011** — As a user, I want to change the hotkey in case it conflicts with another app shortcut.

**US-012** — As a user, I want to choose which local model to use for optimization (Ollama model name or LM Studio).

**US-013** — As a user, I want the app to start automatically with Windows.

**US-014** — As a user, I want to temporarily pause PromptImprover without quitting it.

---

## 5. Functional Requirements

### FR-01: Global Hotkey Listener
- MUST capture a configurable key combination system-wide (default: Ctrl+Shift+P)
- MUST work in foreground: browser windows, terminal emulators, native GUI apps
- MUST NOT intercept the hotkey when the overlay is already open
- MUST release the keyboard hook cleanly on app exit

### FR-02: Text Capture
- MUST capture the text currently typed in the active input field
- PRIMARY strategy: save clipboard → select all in field → copy → restore clipboard
- FALLBACK strategy: if select-all fails (e.g., read-only fields), use whatever is in the clipboard
- MUST restore original clipboard content after capture regardless of outcome
- MUST handle empty captures gracefully (show a "no text detected" message, do not call LLM)

### FR-03: App Context Detection
- MUST detect the following apps by process name and/or window title:
  - `chrome.exe` / `msedge.exe` with title containing "Claude" → context: `claude_web`
  - Process name `claude.exe` → context: `claude_desktop`
  - Process name `opencode.exe` OR terminal with title containing "opencode" → context: `opencode`
  - Terminal with title containing "gemini" → context: `gemini_cli`
  - Process name `hermes.exe` → context: `hermes`
  - Anything else → context: `generic`
- MUST expose detected context to optimizer and learning modules
- MUST update detection on every hotkey press (not cached across presses)

### FR-04: Prompt Optimizer
- MUST call a local LLM endpoint (Ollama or LM Studio) with a structured meta-prompt
- Meta-prompt MUST include:
  - System role: "You are a prompt engineering expert..."
  - User persona section (from profile)
  - Target app context and its conventions
  - History signal (recent acceptance pattern, if ≥5 samples exist)
  - The raw prompt to optimize
- MUST return only the optimized prompt text — no explanation, no preamble
- MUST enforce a configurable timeout (default: 10s); on timeout, show error in overlay
- MUST handle LLM server not running with a clear error message ("Ollama not running — start it with `ollama serve`")

### FR-05: Overlay UI
- MUST appear as a floating, always-on-top window
- MUST display:
  - Header with detected app context icon + name
  - Original prompt (scrollable, read-only)
  - Optimized prompt (scrollable, editable after clicking "Edit")
  - Three buttons: Accept, Edit, Dismiss
  - Optimization latency (e.g., "1.3s via mistral")
- MUST support keyboard shortcuts within overlay:
  - Enter → Accept
  - Escape → Dismiss
  - Ctrl+E → Edit mode
- On Accept: inject optimized text into source field via clipboard
- On Dismiss: close overlay, leave source field unchanged
- MUST close automatically after 30 seconds of inactivity

### FR-06: Learning Engine
- MUST record every optimization attempt in SQLite with:
  - Timestamp
  - App context
  - Original prompt (hashed for privacy if user prefers)
  - Optimized prompt
  - User action: `accepted` | `edited` | `dismissed`
  - Edited text (if applicable)
  - Model used
  - Latency
- MUST compute per-app acceptance rate after ≥5 samples
- MUST include a one-line summary of acceptance pattern in meta-prompt after ≥5 samples
  - e.g., "User usually accepts prompts that add explicit output format requirements."
- MUST NOT use raw prompt text in meta-prompt history (only behavioral patterns)

### FR-07: System Tray
- MUST show a tray icon when running
- Tray menu MUST include:
  - Toggle enabled/disabled (pause optimization)
  - Open settings (config editor)
  - Edit persona
  - View prompt history
  - Quit
- MUST show a brief toast notification on first successful optimization

### FR-08: Configuration
- Config file: `config.toml` in app root
- MUST support: hotkey, model backend, model name, host URL, timeout, persona fields, learning toggle
- MUST validate config on startup and report errors before loading tray

---

## 6. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | Hotkey-to-overlay time ≤ 2 seconds on a machine running Ollama with a 7B model |
| NFR-02 | App memory footprint ≤ 80MB when idle |
| NFR-03 | Must not crash the host application if text capture fails |
| NFR-04 | All prompt data stays local — no network calls except to `localhost` |
| NFR-05 | SQLite DB must not grow beyond 50MB (auto-prune entries older than 90 days) |
| NFR-06 | Must handle Ollama being unavailable gracefully (no hanging, no silent failure) |

---

## 7. UX Flows

### 7.1 Happy Path

```
[User in Claude Desktop] → types prompt → presses Ctrl+Shift+P
→ clipboard saved → select all + copy
→ app detected: claude_desktop
→ Ollama called with assembled meta-prompt
→ overlay appears (< 2s)
→ user reviews → presses Enter
→ optimized text injected back → original clipboard restored
→ history recorded: accepted
```

### 7.2 LLM Timeout

```
→ Ollama called → no response in 10s
→ overlay shows: "Optimization timed out. Try a faster model or check Ollama."
→ Dismiss button only
→ source field unchanged
```

### 7.3 Empty Capture

```
→ hotkey pressed in an app with no editable field
→ clipboard returns empty
→ toast: "Nothing to optimize — click into a text field first."
→ no overlay shown
```

### 7.4 User Edits Before Accepting

```
→ overlay shown → user clicks "Edit"
→ optimized text becomes editable
→ user makes changes → clicks "Accept"
→ edited text injected
→ history recorded: edited (stores both optimized + final edited text)
```

---

## 8. Privacy Considerations

- Prompt content stored in SQLite is accessible only on the local machine
- Users can disable history storage in config (`learning.enabled = false`)
- Users can clear history via tray menu → "Clear prompt history"
- No telemetry, no analytics, no external calls
- Raw prompts are stored as plain text by default; a future option to hash them is planned

---

## 9. Open Questions

| # | Question | Owner | Status |
|---|---|---|---|
| OQ-01 | Should the overlay support rich diff highlighting (word-level changes)? | Yashash | Open |
| OQ-02 | Should the app support multiple personas and let the user switch? | Yashash | Open |
| OQ-03 | For terminal apps, is clipboard injection reliable enough, or do we need xdotool-equivalent for Windows? | Engineering | Open |
| OQ-04 | What's the minimum Ollama model that gives acceptable optimization quality? | Yashash | Open |
