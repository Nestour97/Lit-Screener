"""
LLM client — OpenAI | Anthropic | Groq.
API keys are read from os.environ at call time (not import time),
so setting them in the Streamlit sidebar always takes effect.
"""

import os
import json
import logging
from typing import Optional

from src.utils.retry_utils import with_retry

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

GROQ_JSON_CAPABLE = {
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
}


def _cfg(key: str, default: str = "") -> str:
    """Read config from env at call time — never cached at import time."""
    return os.environ.get(key, default)


class LLMClient:
    """Provider-agnostic LLM wrapper. Supports openai | anthropic | groq."""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = (provider or _cfg("LLM_PROVIDER", "groq")).lower()
        self.model = model or self._default_model()

    def _default_model(self) -> str:
        defaults = {
            "openai": "gpt-4o",
            "anthropic": "claude-opus-4-6",
            "groq": "llama-3.3-70b-versatile",
        }
        return _cfg(f"{self.provider.upper()}_MODEL", defaults.get(self.provider, ""))

    # ── Public API ────────────────────────────────────────────────────────────

    def complete(self, system: str, user: str,
                 max_tokens: int = 4096,
                 temperature: float = 0.0) -> str:
        return self._complete_with_retry(system, user, max_tokens, temperature)

    def complete_json(self, system: str, user: str, max_tokens: int = 4096) -> dict:
        raw = self.complete(system, user, max_tokens)
        return _parse_json_safe(raw)

    # ── Retry wrapper ─────────────────────────────────────────────────────────

    @with_retry(max_attempts=3, base_delay=2.0)
    def _complete_with_retry(self, system, user, max_tokens, temperature) -> str:
        if self.provider == "anthropic":
            return self._anthropic_complete(system, user, max_tokens, temperature)
        elif self.provider in ("openai", "groq"):
            return self._openai_compat_complete(system, user, max_tokens, temperature)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    # ── Anthropic ─────────────────────────────────────────────────────────────

    def _anthropic_complete(self, system, user, max_tokens, temperature) -> str:
        try:
            import anthropic
        except ImportError:
            raise ImportError("Run: pip install anthropic")

        api_key = _cfg("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it in the Streamlit sidebar or in your .env / Streamlit secrets."
            )

        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text if resp.content else ""

    # ── OpenAI / Groq (same SDK) ──────────────────────────────────────────────

    def _openai_compat_complete(self, system, user, max_tokens, temperature) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Run: pip install openai")

        if self.provider == "groq":
            api_key = _cfg("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY is not set.")
            client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
            use_json = self.model in GROQ_JSON_CAPABLE
        else:
            api_key = _cfg("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is not set.")
            client = OpenAI(api_key=api_key)
            use_json = True

        kwargs = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if use_json:
            kwargs["response_format"] = {"type": "json_object"}

        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""


def _parse_json_safe(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc
