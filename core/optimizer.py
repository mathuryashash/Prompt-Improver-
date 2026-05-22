import json
import re
import time

import requests
from dataclasses import dataclass
from core.app_detector import AppContext

from core.paths import get_resource_path

_TEMPLATE_PATH = get_resource_path("prompt_templates/meta_prompt.json")

MAX_PROMPT_CHARS = 3000

# Lines that indicate the model leaked meta-commentary after the rewrite
_STRIP_PATTERNS = [
    r"(?i)^please provide this optimized prompt",
    r"(?i)^this optimized prompt (will|should|can)",
    r"(?i)^note:",
    r"(?i)^explanation:",
    r"(?i)^i hope this",
    r"(?i)^feel free to",
    r"(?i)^let me know if",
    r"(?i)^return only",
    r"(?i)^in summary",
]


def _load_template() -> dict:
    try:
        return json.loads(_TEMPLATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {
            "system": "You are an expert prompt engineer. Diagnose what is weak in the raw prompt, then rewrite it. Format: ANALYSIS: bullet list\nOPTIMIZED PROMPT: the rewrite only.",
            "conventions": {},
            "examples": [],
            "recency_cue": "Output ANALYSIS: then OPTIMIZED PROMPT: only.",
        }


@dataclass
class OptimizationResult:
    optimized_text: str
    model: str
    latency_ms: int


class Optimizer:
    def __init__(self, config):
        self.config = config
        self._template = _load_template()

    def optimize(
        self,
        raw_prompt: str,
        app_context: AppContext,
        persona_role: str,
        persona_domain: str,
        persona_style: str,
        history_signal: str | None = None,
    ) -> OptimizationResult:
        if len(raw_prompt) > MAX_PROMPT_CHARS:
            raise ValueError(
                f"Prompt too long ({len(raw_prompt):,} chars). "
                f"Select a specific section (max {MAX_PROMPT_CHARS:,} chars)."
            )

        messages = self._build_messages(
            raw_prompt, app_context, persona_role,
            persona_domain, persona_style, history_signal,
        )

        start = time.time()
        raw_output = self._call_llm(messages)
        latency_ms = int((time.time() - start) * 1000)

        return OptimizationResult(
            optimized_text=_extract_optimized_prompt(raw_output),
            model=self.config.model_name,
            latency_ms=latency_ms,
        )

    def _build_messages(self, raw, ctx, role, domain, style, signal) -> list[dict]:
        t = self._template
        messages = []

        # 1. System — role + rules + output format contract
        messages.append({"role": "system", "content": t["system"]})

        # 2. Transformation examples (few-shot) — best example is last (recency effect)
        examples = t.get("examples", [])
        # put the app-matching example last if one exists
        app_example = next((e for e in examples if e.get("app") == ctx.id), None)
        other_examples = [e for e in examples if e.get("app") != ctx.id]
        ordered = other_examples + ([app_example] if app_example else [])

        for ex in ordered:
            messages.append({"role": "user", "content": ex["user"]})
            messages.append({"role": "assistant", "content": ex["assistant"]})

        # 3. Build single consolidated user message with conventions, persona, and raw prompt
        conventions = t.get("conventions", {})
        app_convention = conventions.get(ctx.id, conventions.get("generic", ""))

        persona_lines = [
            "USER PERSONA:",
            f"- Role: {role}",
            f"- Domain: {domain}",
            f"- Style: {style}",
        ]
        if signal:
            persona_lines += ["", "BEHAVIOUR PATTERN:", signal]

        user_parts = [
            f"TARGET APP: {ctx.display_name}",
        ]
        if app_convention:
            user_parts.append(f"App Conventions: {app_convention}")
        user_parts.append("\n".join(persona_lines))
        user_parts.append(f"RAW PROMPT: {raw}")
        
        recency_cue = t.get("recency_cue", "Output THOUGHT: and OPTIMIZED PROMPT: following the critical rules.")
        user_parts.append(recency_cue)

        messages.append({
            "role": "user",
            "content": "\n\n".join(user_parts)
        })

        return messages

    def _call_llm(self, messages: list[dict]) -> str:
        cfg = self.config
        temperature = getattr(cfg, "temperature", 0.4)

        if cfg.backend == "ollama":
            resp = requests.post(
                f"{cfg.host}/api/chat",
                json={
                    "model": cfg.model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_ctx": 4096,
                        "temperature": temperature,
                        "num_predict": 800,   # more room for analysis + rewrite
                        "stop": ["\nRAW PROMPT:", "\nUSER PERSONA:"],
                    },
                },
                timeout=cfg.timeout,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

        elif cfg.backend == "lmstudio":
            resp = requests.post(
                f"{cfg.host}/v1/chat/completions",
                json={
                    "model": cfg.model_name,
                    "messages": messages,
                    "max_tokens": 800,
                    "temperature": temperature,
                },
                timeout=cfg.timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

        else:
            raise ValueError(f"Unknown backend: {cfg.backend}")


def _extract_optimized_prompt(text: str) -> str:
    """
    Parse the model's output to extract only the OPTIMIZED PROMPT section,
    stripped of meta-commentary.
    Falls back to cleaning and returning the full output if the marker isn't found.
    """
    text = text.strip()

    # Try to find the OPTIMIZED PROMPT section
    marker_patterns = [
        r"OPTIMIZED PROMPT:\s*\n",
        r"OPTIMIZED PROMPT:\s*",
        r"Optimized Prompt:\s*\n",
        r"Optimized prompt:\s*\n",
    ]
    for pattern in marker_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            optimized = text[match.end():].strip()
            return _strip_trailing_noise(optimized)

    # Fallback: model didn't use the format — clean and return everything
    # (strip any leading ANALYSIS or THOUGHT section if present)
    analysis_match = re.search(r"^ANALYSIS:.*?\n+", text, re.IGNORECASE | re.DOTALL)
    if analysis_match:
        text = text[analysis_match.end():].strip()
    thought_match = re.search(r"^THOUGHT:.*?\n+", text, re.IGNORECASE | re.DOTALL)
    if thought_match:
        text = text[thought_match.end():].strip()

    return _strip_trailing_noise(text)


def _strip_trailing_noise(text: str) -> str:
    """Remove meta-commentary lines that small models sometimes append."""
    lines = text.splitlines()
    clean = []
    for line in lines:
        if any(re.search(p, line) for p in _STRIP_PATTERNS):
            break
        clean.append(line)
    result = "\n".join(clean).rstrip()
    return result if result.strip() else text  # never return empty — fallback to original
