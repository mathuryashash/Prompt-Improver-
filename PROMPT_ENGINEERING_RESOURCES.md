# Prompt‑Engineering Resources – Consolidated Guide

*Compiled from public documentation and tutorials (Google Cloud, Microsoft Azure OpenAI, OpenAI, Anthropic Claude, Hugging Face, GitLab, and related community resources). All links are preserved for attribution and further reading.*

---

## Table of Contents

1. [What is Prompt Engineering?](#what-is-prompt-engineering)  
2. [Universal Prompt Blueprint](#universal-prompt-blueprint)  
3. [Core Techniques (cross‑platform)](#core-techniques-cross-platform)  
4. [Platform‑Specific Guidance]  
   - [Google Cloud – Prompt Engineering for Generative AI](#google-cloud-prompt-engineering)  
   - [Microsoft Azure OpenAI – Prompt Techniques](#microsoft-azure-openai-prompt-techniques)  
   - [OpenAI – Prompt Engineering Guide](#openai-prompt-engineering-guide)  
   - [Anthropic Claude – Prompt Overview & Console Tools](#anthropic-claude-prompt-overview)  
   - [Hugging Face – Prompting Docs](#hugging-face-prompting-docs)  
   - [GitLab – Prompt‑Engineering Guide](#gitlab-prompt-engineering-guide)  
5. [Prompt‑Engineering Checklist](#prompt-engineering-checklist)  
6. [Useful Links – Quick Reference](#useful-links-quick-reference)  
7. [Applying the Guide to the **PromptImprover** Repository](#applying-the-guide-to-promptimprover)  

---

## What is Prompt Engineering? <a name="what-is-prompt-engineering"></a>

Prompt engineering is the art & science of crafting **instructions + data** that steer a large language model (LLM) to produce the desired output **reliably**, **efficiently**, and **safely**.  

Key ideas (common across providers):

| Concept | Why it matters | Typical implementation |
|--------|----------------|-----------------------|
| **Prompt = role + goal + instructions + context** | LLMs are next‑token predictors; exact wording & ordering directly affect output. | System (or `<system>`) message for role, followed by user content containing primary data and constraints. |
| **Determinism vs. creativity** | Temperature, top‑p, and model size control randomness. | `temperature=0.0‑0.2` for factual output; `0.6‑0.9` for brainstorming. |
| **Model‑specific quirks** | Each provider interprets tags, roles, and “effort” differently. | Use XML tags for Claude, `system`/`assistant` roles for OpenAI/Azure/Google. |
| **Grounding / Retrieval‑Augmented Generation (RAG)** | Supplies up‑to‑date or proprietary facts that the model otherwise doesn’t know. | Prefix the prompt with `Context:` or `{{retrieved}}` blocks. |
| **Iterative refinement** | Rarely perfect on first try – a “test‑>‑tweak‑>‑retest” loop yields high acceptance rates. | Run a few edge‑cases, adjust wording, reorder sections, add examples. |

---

## Universal Prompt Blueprint <a name="universal-prompt-blueprint"></a>

The following skeleton works for **OpenAI, Azure OpenAI, Google Gemini, Anthropic Claude, Hugging Face**, and most custom inference pipelines.

```text
<ROLE / SYSTEM>
You are a <persona> (e.g., helpful coding assistant, concise research analyst).  
Maintain <tone/style> and obey the constraints below.

<OBJECTIVE>
Your goal is to <task description> (e.g., “generate a concise JSON summary”).

<INSTRUCTIONS>
1. Do X.  
2. Do Y.  
3. Do Z.  
- Output format: <JSON / XML / Markdown / plain text>.  
- Constraints: <max tokens>, <no markdown if not wanted>, <no hallucinations>, etc.

<EXAMPLES>          (optional few‑shot)
User: <example input 1>
Assistant: <example output 1>
... 
User: <example input N>
Assistant: <example output N>

<CONTEXT / SUPPORTING DATA>
<document>
{{LONG_TEXT_OR_FILE_CONTENT}}
</document>

<CUE / PRIME>
Here is the answer:
```

**Mapping to each provider**

| Provider | How to express sections |
|----------|--------------------------|
| **OpenAI / Azure OpenAI** | `system` = ROLE + OBJECTIVE + INSTRUCTIONS. `user` = CONTEXT + raw query. Optional `assistant` = EXAMPLES. |
| **Google Gemini** | Same as OpenAI (system optional). Use markdown or XML tags inside the user message. |
| **Anthropic Claude** | Wrap each logical block in XML tags (`<system>…</system>`, `<instruction>…</instruction>`, `<example>…</example>`, `<document>…</document>`). Everything can be a single user message. |
| **Hugging Face** | Single string following the order above. |
| **GitLab** | Same as OpenAI; store the template file in the repo for versioning. |
```
---

## Core Techniques (Cross‑Platform) <a name="core-techniques-cross-platform"></a>

| Technique | When to use | Prompt pattern (example) | Source |
|-----------|--------------|--------------------------|--------|
| **Zero‑shot** | Simple tasks, quick prototype | `Summarize the following article in two sentences:` | Google Cloud “Direct prompting (Zero‑shot)” |
| **Few‑shot / One‑shot** | Need strict output shape (JSON, classification) | ```User: {"text":"I love this!"}\nAssistant: {"sentiment":"positive"}``` | Microsoft “Few‑shot learning” |
| **Chain‑of‑thought (CoT)** | Complex reasoning, math, planning | `Let’s think step‑by‑step:` (prepend) | OpenAI “Chain‑of‑thought prompting” |
| **Zero‑shot CoT** | Want CoT without examples | `Let’s think step by step.` after the main instruction | Google Cloud “Zero‑shot CoT” |
| **Prompt Cues** | Force formatting (bullets, code fences) | `Answer in a markdown list:\n- ` | Microsoft “Cue” |
| **Role‑prompting** | Give persona, tone, domain expertise | `You are a senior software engineer specializing in Rust.` (system) | OpenAI “Message roles” |
| **Temperature / Top‑p** | Control creativity vs. determinism | `temperature=0.2` for factual; `0.8` for brainstorming | OpenAI “Choosing a model” |
| **Constraints** | Limit length, avoid ellipses, enforce output format | `Respond in ≤ 3 sentences.` | Google Cloud “Use constraints” |
| **Structured Outputs** | Require parsable JSON/YAML/CSV | `Return JSON: {"answer": "...", "confidence": 0.9}` | OpenAI “Structured outputs” |
| **Grounding / RAG** | Need up‑to‑date facts or proprietary data | `Context: {{retrieved_document}}` then ask the question | Microsoft “Provide relevant context information” |
| **Reusable prompts** | Reduce latency & cost for repeated patterns | Define prompt with variables `{{user_input}}` in the console/dashboard. | OpenAI “Reusable prompts” |
| **Iterative refinement** | First trial fails → edit & retest | Follow “Prompt iteration strategies” (repeat keywords, add constraints, use all‑caps). | Google Cloud “Prompt iteration strategies” |

---

## Platform‑Specific Guidance  

### Google Cloud – Prompt Engineering for Generative AI <a name="google-cloud-prompt-engineering"></a>
*Source: <https://developers.google.com/machine-learning/resources/prompt-eng>*

| Topic | Key Takeaways |
|-------|---------------|
| **Best Practices** | 1️⃣ Communicate what’s most important. 2️⃣ Structure: role → context → instruction. 3️⃣ Provide varied examples. 4️⃣ Use constraints to limit scope. 5️⃣ Break complex tasks into steps. |
| **Prompt Types** | Zero‑shot, One‑shot, Few‑shot, Chain‑of‑thought, Zero‑shot CoT. |
| **Iteration Strategies** | Repeat key words, specify output format, use ALL‑CAPS for emphasis, “sandwich” technique (repeat instruction at start & end), use prompt libraries for inspiration. |
| **Additional Resources** | Prompt generator, prompt library, “Learn Prompt” interactive tutorial. |

---

### Microsoft Azure OpenAI – Prompt Techniques <a name="microsoft-azure-openai-prompt-techniques"></a>
*Source: <https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/prompt-engineering>*

| Section | Highlights |
|---------|------------|
| **Instructions** | Write clear, concrete steps. Example: “Write an intro for a weekly newsletter for Contoso, mention the all‑hands meeting, thank the team.” |
| **Primary Content** | The text you want processed (translation, summarization, classification). |
| **Examples (Few‑shot)** | Provide input‑output pairs; keep them concise and diverse. |
| **Cue** | Prefix like `Here is the answer:` to steer output. |
| **Supporting Content** | Add context (date, user name, preferences) before the request. |
| **Scenario‑Specific Guidance** | Use grounding (RAG) for up‑to‑date facts, break tasks, ask the model to self‑check. |
| **Temperature / Top‑p** | Lower for legal/technical output, higher for creative work. |
| **Best Practices Summary** | Be specific, descriptive, repeat constraints, order matters, give an “out” (e.g., “reply ‘not found’ if answer missing”). |
| **Space Efficiency** | Prefer tables over verbose key‑value pairs; minimise whitespace. |

---

### OpenAI – Prompt Engineering Guide <a name="openai-prompt-engineering-guide"></a>
*Source: <https://platform.openai.com/docs/guides/prompt-engineering>*

| Area | Essentials |
|------|-----------|
| **Message Roles** | `system` (high‑priority instructions), `user` (task & data), `assistant` (model response). |
| **System Prompt** | Set persona, tone, constraints – highest priority. |
| **Few‑shot** | Add `assistant` messages as examples after the system prompt. |
| **Structured Outputs** | Use JSON schema; enforce via “output must be valid JSON”. |
| **Reusable Prompts** | Define a prompt ID + variables in the dashboard; call via `prompt: {id, variables}`. |
| **Temperature & Top‑p** | Same 0‑2 range; lower for factual tasks. |
| **Best Practices** | Put frequently‑used content near the beginning for prompt caching, keep instructions short & explicit, avoid “don’t …” phrasing, use positive language. |
| **Tool Use** | Explicitly say “use the search tool when …”. |
| **Chain‑of‑Thought** | “Let’s think step‑by‑step.” works well for reasoning. |

---

### Anthropic Claude – Prompt Overview & Console Tools <a name="anthropic-claude-prompt-overview"></a>
*Sources: <https://docs.claude.com/claude/docs/introduction-to-prompt-design>, <https://docs.anthropic.com/en/docs/prompt-generator>*

| Feature | Details |
|---------|---------|
| **Prompt Format** | Use XML‑style tags (`<system>`, `<instruction>`, `<example>`, `<document>`) in a **single user message**. |
| **Role Prompting** | `You are a helpful coding assistant…` inside `<system>` or at the top. |
| **Few‑shot** | Add `<example>` blocks with `<user>`/`<assistant>` pairs. |
| **Prompt Generator** | Interactive tool that asks for the task and returns a skeleton with `{{variable}}` placeholders. |
| **Prompt Improver** | Takes an existing template, adds chain‑of‑thought reasoning, refactors XML tags, and generates richer examples. |
| **Reusable Variables** | `{{variable}}` placeholders can be filled via the API. |
| **Prefill Removal** | From Claude Opus 4.6 onward, last‑assistant prefilled messages are unsupported – use structured output or ask the model to “respond directly”. |
| **Effort Parameter** | Controls reasoning depth: `low`, `medium`, `high`, `xhigh`, `max`. Higher effort → more thinking, higher latency. |
| **Tool Use** | Explicit instructions like “When you need external data, call the `search` tool”. |
| **Cues & Recency** | Repeat critical constraints at the end of the prompt to mitigate recency bias. |

---

### Hugging Face – Prompting Docs <a name="hugging-face-prompting-docs"></a>
*Source: <https://huggingface.co/docs/transformers/tasks/prompting>*

| Highlight |
|----------|
| Works with both **base** (e.g., Llama 2) and **instruction‑tuned** models. |
| Prompt format is a single string; you can embed `<pad>` tokens, system prompts, or special `<bos>` markers depending on the model. |
| **Few‑shot** – concatenate examples as plain text. |
| **Chain‑of‑thought** – prepend “Let’s think step‑by‑step”. |
| **Temperature & Top‑p** – same range as other providers. |
| **Best Practices** – be specific, use examples, keep the instruction part near the start, add a cue at the end. |

---

### GitLab – Prompt‑Engineering Guide <a name="gitlab-prompt-engineering-guide"></a>
*Source: <https://docs.gitlab.com/development/ai_features/prompt_engineering/>*

| Core Points |
|-------------|
| Prompt = **Task description + Context + Desired output format**. |
| Emphasise **clarity** and **examples**. |
| Use **structured output** (JSON/YAML) for downstream parsers. |
| Encourage **testing** – write unit‑style evals for prompts. |
| Track **versioning** of prompts (e.g., keep a `prompts/` repo folder). |
| Follow safety guardrails: “If unsure, say *I don’t know*.” |
| Use **prompt‑caching** where possible (GitLab’s AI service supports it). |

---

## Prompt‑Engineering Checklist <a name="prompt-engineering-checklist"></a>

1. **Goal** – one‑sentence statement of what the model must deliver.  
2. **Persona / Role** – system message or `<system>` tag.  
3. **Explicit Instructions** – numbered steps, constraints, output format.  
4. **Few‑shot Examples** (if output shape is strict).  
5. **Primary Content** – the user‑provided text / code / data.  
6. **Supporting Context** – RAG data, tables, metadata (place *before* the instruction if you want caching).  
7. **Cue / Recency Reinforcement** – repeat the most critical constraint at the end.  
8. **Temperature / Effort** – set appropriately (low for factual, high for creative).  
9. **Validate** – run a small test suite (edge cases, length limits).  
10. **Iterate** – adjust ordering, wording, add examples, re‑test.  
11. **Version & Store** – keep the final prompt in source control (e.g., `prompts/` folder).  

---

## Useful Links – Quick Reference <a name="useful-links-quick-reference"></a>

| Provider | Topic | URL |
|----------|------|-----|
| **Google Cloud** | Prompt Engineering for Generative AI | <https://developers.google.com/machine-learning/resources/prompt-eng> |
| **Microsoft Azure OpenAI** | Prompt Techniques | <https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/prompt-engineering> |
| **OpenAI** | Prompt Engineering Guide | <https://platform.openai.com/docs/guides/prompt-engineering> |
| **Anthropic Claude** | Prompt Design Overview | <https://docs.claude.com/claude/docs/introduction-to-prompt-design> |
| **Anthropic Console** | Prompt Generator & Improver | <https://docs.anthropic.com/en/docs/prompt-generator> |
| **Hugging Face** | Prompting Docs (Transformers) | <https://huggingface.co/docs/transformers/tasks/prompting> |
| **GitLab** | Prompt‑Engineering Guide | <https://docs.gitlab.com/development/ai_features/prompt_engineering/> |
| **OpenAI Structured Outputs** | JSON/YAML response contracts | <https://platform.openai.com/docs/guides/structured-outputs> |
| **OpenAI Reusable Prompts** | Dashboard prompt templates | <https://platform.openai.com/docs/guides/prompt-caching> |
| **Claude Prompt Library** | Community prompt collection | <https://prompthero.com/> |
| **Claude Interactive Tutorial** | Hands‑on notebook | <https://github.com/anthropics/prompt-eng-interactive-tutorial> |
| **OpenAI Playground** | Live prompt experimentation | <https://platform.openai.com/playground> |
| **Google Prompt Gallery** | Sample prompts for Gemini | <https://developers.generativeai.google/prompt-gallery> |
| **Microsoft Prompt Library** | Sample prompts & patterns | <https://learn.microsoft.com/en-us/azure/ai-services/openai/prompt-library> |

---

## Applying the Guide to **PromptImprover** (your repository) <a name="applying-the-guide-to-promptimprover"></a>

Your current implementation builds a *meta‑prompt* that merges:

* Persona (from `config.toml`)  
* App‑specific conventions (`app_context.conventions`)  
* Optional learning‑signal (history summary)  
* The raw user prompt  

**Improvements you can make right now:**

1. **Adopt the universal skeleton** – add a distinct `<CUE>` section that repeats the “output‑only” rule at the very end (helps with recency bias).  
2. **Use positive phrasing** – replace “Do not …” with “Please respond with …”.  
3. **Add a few‑shot example** for each supported app (Claude Desktop, Gemini CLI, etc.) so the model sees the exact format you expect.  
4. **Explicit output format** – e.g., `Return ONLY the optimized prompt as plain text, no markdown, no backticks.`  
5. **Expose an `effort`/`temperature` option** in `config.toml` so power users can trade latency for reasoning depth.  
6. **Recency reinforcement** – repeat the core constraint after the examples and before the raw prompt.  
7. **Version the prompt** – store it as `prompt_templates/meta_prompt.txt` (or `.json` if you prefer the OpenAI messages format). Load it at runtime so you can edit without touching code.  
8. **Prompt caching** – the constant parts (system message, conventions, examples) can be cached by the LLM provider, reducing latency.  

**Sample updated meta‑prompt (OpenAI‑style, ready for `optimizer.py`):**

```json
{
  "model": "{{model_name}}",
  "messages": [
    {"role": "system", "content": "You are an expert prompt‑engineer. Rewrite the user's rough prompt into a concise, model‑ready prompt.\n\nConstraints:\n- Output ONLY the rewritten prompt; no preamble, no explanation, no markdown.\n- Preserve the user's intent and required details.\n- Follow the style guidelines for the target application (see below)."},
    {"role": "assistant", "content": "<CONVENTIONS>\nClaude Desktop: detailed, explicit output format, no emojis.\nGemini CLI: terse, one‑liner, no prose.\nOpencode: include language, file name, tests.\nGeneric: short, clear, include desired output format.\n</CONVENTIONS>"},
    {"role": "assistant", "content": "<HISTORY>\n{{history_signal_if_any}}\n</HISTORY>"},
    {"role": "assistant", "content": "<EXAMPLES>\nUser: Write a function that sorts a list.\nAssistant: Write a Python function that sorts a list of dictionaries by the key `timestamp` in descending order, handling `None` values safely.\n</EXAMPLES>"},
    {"role": "user", "content": "RAW PROMPT:\n{{raw_prompt}}\n\nRewrite the prompt according to the rules above.\n"}
  ],
  "temperature": {{temperature}},
  "max_tokens": 512
}
``` 

Store the JSON (or a plain‑text version with XML tags) in `prompt_templates/meta_prompt.json` and load it in `optimizer.py`.  

Doing so gives you:
* **Consistent, version‑controlled prompts** – easy to tweak and A/B test.  
* **Better compliance** – explicit “output‑only” cue at both top and bottom reduces hallucination.  
* **Faster responses** – constant sections can be cached.  
* **More control** – users can tune `temperature`/`effort` via config.  

---

**That’s the complete markdown file you asked for.** Save it alongside your code and refer to it whenever you need a prompt‑engineering reference or want to improve PromptImprover’s meta‑prompt. 🎉
