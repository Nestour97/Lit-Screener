"""
LLM client with provider abstraction (OpenAI default; Anthropic stub).
All calls return raw text. Structured JSON parsing is done by callers.
"""

import json
import logging
from typing import Optional

from src.config import (
    LLM_PROVIDER, OPENAI_API_KEY, ANTHROPIC_API_KEY,
    OPENAI_MODEL, ANTHROPIC_MODEL, MAX_TOKENS, TEMPERATURE,
    RETRY_MAX_ATTEMPTS, RETRY_BASE_DELAY
)
from src.utils.retry_utils import with_retry

logger = logging.getLogger(__name__)


class LLMClient:
    """Provider-agnostic LLM wrapper."""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = (provider or LLM_PROVIDER).lower()
        if self.provider == "openai":
            self.model = model or OPENAI_MODEL
            self._client = self._init_openai()
        elif self.provider == "anthropic":
            self.model = model or ANTHROPIC_MODEL
            self._client = self._init_anthropic()
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    # ── Initialisation ────────────────────────────────────────────────────────

    def _init_openai(self):
        try:
            from openai import OpenAI
            return OpenAI(api_key=OPENAI_API_KEY)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def _init_anthropic(self):
        try:
            import anthropic
            return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    # ── Public API ─────────────────────────────────────────────────────────────

    def complete(self, system: str, user: str, max_tokens: int = MAX_TOKENS,
                 temperature: float = TEMPERATURE) -> str:
        """Send a chat completion and return the raw text response."""
        return self._complete_with_retry(system, user, max_tokens, temperature)

    def complete_json(self, system: str, user: str, max_tokens: int = MAX_TOKENS) -> dict:
        """Send a completion expecting JSON back. Strips markdown fences."""
        raw = self.complete(system, user, max_tokens)
        return _parse_json_safe(raw)

    # ── Provider implementations ──────────────────────────────────────────────

    @with_retry(max_attempts=RETRY_MAX_ATTEMPTS, base_delay=RETRY_BASE_DELAY)
    def _complete_with_retry(self, system: str, user: str,
                             max_tokens: int, temperature: float) -> str:
        if self.provider == "openai":
            return self._openai_complete(system, user, max_tokens, temperature)
        elif self.provider == "anthropic":
            return self._anthropic_complete(system, user, max_tokens, temperature)

    def _openai_complete(self, system: str, user: str,
                         max_tokens: int, temperature: float) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or ""

    def _anthropic_complete(self, system: str, user: str,
                            max_tokens: int, temperature: float) -> str:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text if resp.content else ""


def _parse_json_safe(raw: str) -> dict:
    """Strip markdown fences and parse JSON. Raises ValueError on failure."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error(f"[llm_client] JSON parse error: {exc}\nRaw: {raw[:300]}")
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc
