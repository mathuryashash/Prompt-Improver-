# Roadmap — PromptImprover

**Version:** 1.0  
**Last Updated:** 2026-05-19

---

## Guiding Principle

Ship the smallest thing that closes the gap between "thought" and "precision prompt". Every phase must deliver something usable before adding intelligence.

---

## Phase 0 — Proof of Concept (1–2 days)

**Goal:** Prove the core mechanic works end-to-end, even if rough.

**Deliverables:**
- [ ] Global hotkey fires (pynput working on Windows)
- [ ] Clipboard capture and restore works reliably
- [ ] Hard-coded call to Ollama returns an optimized prompt
- [ ] Simple tkinter popup shows original vs. optimized
- [ ] Accept replaces text in the source field

**Acceptance criteria:** You can type a vague prompt in Notepad, press Ctrl+Shift+P, see an improved version, and accept it — with the optimized text appearing in Notepad.

**Not included:** App detection, learning, tray, config file.

---

## Phase 1 — MVP (1 week)

**Goal:** A real, installable app you can use daily.

**Deliverables:**
- [ ] `config.toml` for hotkey, model, persona
- [ ] App context detection (claude_desktop, claude_web, opencode, gemini_cli, hermes, generic)
- [ ] Per-app meta-prompt conventions
- [ ] System tray with pause/quit
- [ ] Error handling: Ollama not running, timeout, empty capture
- [ ] Overlay with Accept / Edit / Dismiss + keyboard shortcuts (Enter, Esc, Ctrl+E)
- [ ] Auto-dismiss overlay after 30 seconds
- [ ] SQLite history recording (no adaptation yet)

**Acceptance criteria:** App runs silently on boot, works across at least 3 target apps without crashing, handles errors gracefully.

---

## Phase 2 — Learning Engine (1–2 weeks)

**Goal:** The system gets noticeably better the more you use it.

**Deliverables:**
- [ ] `learning/history.py` — acceptance rate tracking
- [ ] `learning/profile.py` — LLM-generated history signal after 5+ samples
- [ ] History signal injected into meta-prompt
- [ ] Persona cache (10-minute TTL to avoid latency spikes)
- [ ] "View History" in tray menu (simple list window showing recent optimizations + outcomes)
- [ ] Acceptance rate displayed in tray tooltip

**Acceptance criteria:** After 20 interactions, the optimization quality measurably shifts toward the user's pattern (subjective test: 3 users evaluate 10 before/after pairs).

---

## Phase 3 — Polish & Reliability (1 week)

**Goal:** Feels like a product, not a script.

**Deliverables:**
- [ ] Word-level diff highlighting in overlay (highlight what changed)
- [ ] App icon and branded system tray icon
- [ ] Toast notifications (not just print() calls)
- [ ] "Start with Windows" registry toggle in tray menu
- [ ] Terminal-aware text capture (Ctrl+Shift+C for terminal emulators)
- [ ] Config validation on startup with human-readable error messages
- [ ] Auto-prune of SQLite history (90-day TTL)
- [ ] Single-file installer (PyInstaller .exe)

**Acceptance criteria:** A fresh user can install the .exe, fill in config.toml, and be running within 5 minutes. No Python knowledge required.

---

## Phase 4 — Advanced Personalization (2–4 weeks)

**Goal:** Deep adaptation that makes the tool feel like it knows you.

**Deliverables:**
- [ ] Multiple saved personas (e.g., "dev mode", "writing mode") switchable from tray
- [ ] Per-app custom instructions (user can write their own app conventions)
- [ ] Prompt templates: save reusable context blocks (e.g., "I'm debugging a FastAPI app with this schema: ...") that get prepended to optimizations
- [ ] Learning by edited text: when user edits the optimized prompt, extract the delta and feed it back as a style signal
- [ ] History browser UI: searchable table with filter by app, date, action
- [ ] Export history to CSV

**Acceptance criteria:** Users can configure the tool to behave differently for "coding" vs. "writing" contexts without touching config.toml.

---

## Phase 5 — Multi-model & Routing (future)

**Goal:** Use the right model for each optimization task.

**Deliverables:**
- [ ] Model routing: short prompts → fast model (phi3:mini), complex prompts → strong model (llama3.1)
- [ ] Side-by-side comparison: show two model outputs and let user pick
- [ ] Streaming support: show optimized prompt word-by-word as it's generated (reduces perceived latency)
- [ ] Support for additional local model servers (Jan.ai, GPT4All)
- [ ] Optional: Claude API backend (for users who want cloud quality with API key)

---

## Known Limitations to Address

| Limitation | Phase |
|---|---|
| `Ctrl+A` doesn't select in terminal emulators | Phase 3 |
| Hotkey doesn't fire in UAC/admin dialogs | Won't fix (OS limitation) |
| Overlay position not smart (always top-right) | Phase 3 |
| No support for non-Latin text input | Phase 4 |
| LM Studio endpoint differs per version | Phase 3 (version detection) |
| No undo after accepting optimization | Phase 4 |

---

## Success Metrics

| Metric | Target | Measurement |
|---|---|---|
| Hotkey-to-overlay latency | < 2 seconds | Measured on 7B model, modern laptop |
| User acceptance rate | ≥ 60% after 4 weeks | Calculated from SQLite |
| Daily active use | User triggers ≥ 5 optimizations/day | Count from history |
| Crash rate | 0 crashes per day of normal use | Manual QA |
| Optimization quality (subjective) | 8/10 prompts judged "clearly better" | User self-report |

---

## Immediate Next Steps (Start Here)

1. Run Phase 0 — validate the core mechanic works on your machine
2. Pick an Ollama model and measure real latency (`ollama run mistral` → time a generation)
3. Test clipboard capture/inject in each target app (Claude, terminal, Hermes)
4. Once Phase 0 works, use IMPLEMENTATION.md to scaffold the full module structure
