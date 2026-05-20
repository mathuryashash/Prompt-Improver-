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
