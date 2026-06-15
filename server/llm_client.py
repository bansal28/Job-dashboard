"""
Shared LLM client for generation, agent tools, Gmail classification, and evals.

Provider selection is local-config first:
- LLM_PROVIDER=openai|groq to force a provider
- LLM_PROVIDER=auto, or unset, prefers OpenAI when OPENAI_API_KEY exists,
  then falls back to Groq when GROQ_API_KEY exists.
"""

from __future__ import annotations

from typing import Any

import requests

try:
    from .settings import get_setting
except ImportError:  # pragma: no cover
    from settings import get_setting


DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"


class LLMConfigurationError(RuntimeError):
    pass


def get_llm_provider(provider: str | None = None, api_key: str | None = None) -> str:
    """Return the active provider name, or an empty string when no key is available."""
    requested = (provider or get_setting("LLM_PROVIDER", "auto") or "auto").strip().lower()

    # Backward compatibility: old call sites passed a Groq key directly.
    if api_key and requested == "auto":
        return "groq"

    if requested in {"openai", "groq"}:
        return requested if _api_key_for(requested, api_key=api_key) else ""

    if requested not in {"", "auto"}:
        raise LLMConfigurationError(f"Unsupported LLM_PROVIDER '{requested}'. Use auto, openai, or groq.")

    if _api_key_for("openai"):
        return "openai"
    if _api_key_for("groq"):
        return "groq"
    return ""


def has_llm_key(provider: str | None = None) -> bool:
    return bool(get_llm_provider(provider=provider))


def configured_llm_label() -> str:
    provider = get_llm_provider()
    if not provider:
        return "not configured"
    return f"{provider}:{_model_for(provider)}"


def call_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int = 1400,
    temperature: float = 0.2,
    model: str | None = None,
    provider: str | None = None,
    api_key: str | None = None,
) -> str:
    active_provider = get_llm_provider(provider=provider, api_key=api_key)
    if not active_provider:
        requested = provider or get_setting("LLM_PROVIDER", "auto")
        if requested in {"openai", "groq"}:
            raise LLMConfigurationError(f"No {requested.upper()}_API_KEY configured.")
        raise LLMConfigurationError("No LLM API key configured. Add OPENAI_API_KEY or GROQ_API_KEY.")

    if active_provider == "openai":
        return _call_openai(system_prompt, user_prompt, max_tokens=max_tokens, model=model, api_key=api_key)
    if active_provider == "groq":
        return _call_groq(
            system_prompt,
            user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
            api_key=api_key,
        )
    raise LLMConfigurationError(f"Unsupported LLM provider '{active_provider}'.")


def _call_openai(
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int,
    model: str | None,
    api_key: str | None,
) -> str:
    key = _api_key_for("openai", api_key=api_key)
    payload = {
        "model": model or _model_for("openai"),
        "max_output_tokens": max_tokens,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OpenAI API error {response.status_code}: {response.text[:500]}")
    return _extract_openai_text(response.json())


def _call_groq(
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int,
    temperature: float,
    model: str | None,
    api_key: str | None,
) -> str:
    key = _api_key_for("groq", api_key=api_key)
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model or _model_for("groq"),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Groq API error {response.status_code}: {response.text[:500]}")
    return response.json()["choices"][0]["message"]["content"]


def _api_key_for(provider: str, api_key: str | None = None) -> str:
    if api_key:
        return api_key
    if provider == "openai":
        return get_setting("OPENAI_API_KEY", "")
    if provider == "groq":
        return get_setting("GROQ_API_KEY", "")
    return ""


def _model_for(provider: str) -> str:
    if provider == "openai":
        return get_setting("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    if provider == "groq":
        return get_setting("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    return ""


def _extract_openai_text(data: dict[str, Any]) -> str:
    if data.get("output_text"):
        return str(data["output_text"])

    parts: list[str] = []
    for item in data.get("output", []) or []:
        for block in item.get("content", []) or []:
            if isinstance(block, dict) and block.get("text"):
                parts.append(str(block["text"]))

    text = "\n".join(part for part in parts if part).strip()
    if text:
        return text
    raise RuntimeError("OpenAI response did not contain text output.")
