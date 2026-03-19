"""
Classification service.
Runs the first LLM pass on every paper to determine eligibility.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from src.config import PROMPTS_DIR, RAW_OUTPUTS_DIR, PROMPT_VERSION
from src.models.schemas import ClassificationResult, LogEntry
from src.services.llm_client import LLMClient
from src.utils.file_utils import read_prompt, write_json
from src.utils.text_utils import truncate_to_tokens

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = PROMPTS_DIR / "classification_prompt.txt"

# Token budget for paper text in the classification call (classification needs less than extraction)
CLASSIFICATION_TEXT_TOKENS = 60_000


def classify_paper(
    paper_id: str,
    full_text: str,
    client: LLMClient,
    save_raw: bool = True,
) -> ClassificationResult:
    """
    Classify one paper. Returns a ClassificationResult.
    On parse failure, retries once with the error included in the prompt.
    """
    system = read_prompt(SYSTEM_PROMPT_PATH)
    truncated_text = truncate_to_tokens(full_text, CLASSIFICATION_TEXT_TOKENS)
    user_msg = f"Paper ID: {paper_id}\n\n---BEGIN PAPER---\n{truncated_text}\n---END PAPER---"

    raw_response = client.complete(system=system, user=user_msg)

    try:
        data = _safe_parse(raw_response)
    except ValueError as exc:
        logger.warning(f"[classifier] JSON parse failed for {paper_id}; retrying with error context.")
        user_retry = user_msg + f"\n\nYour previous response failed JSON parsing: {exc}. Return ONLY valid JSON."
        raw_response = client.complete(system=system, user=user_retry)
        data = _safe_parse(raw_response)

    if save_raw:
        write_json(
            {"paper_id": paper_id, "step": "classification",
             "prompt_version": PROMPT_VERSION, "response": data},
            RAW_OUTPUTS_DIR / f"{paper_id}_classification.json"
        )

    data["paper_id"] = paper_id
    result = ClassificationResult(**_coerce_types(data))
    return result


def _safe_parse(raw: str) -> dict:
    """Parse JSON from LLM response, stripping markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def _coerce_types(data: dict) -> dict:
    """Ensure types match Pydantic expectations."""
    if "year" in data and data["year"] is not None:
        try:
            data["year"] = int(data["year"])
        except (TypeError, ValueError):
            data["year"] = None
    if "confidence" in data:
        try:
            data["confidence"] = float(data["confidence"])
        except (TypeError, ValueError):
            data["confidence"] = 0.5
    data.setdefault("eligible_for_full_extraction", False)
    data.setdefault("needs_review", False)
    data.setdefault("rationale", "")
    return data
