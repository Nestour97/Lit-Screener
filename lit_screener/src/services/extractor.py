"""
Variable extraction service.
Runs the second LLM pass (only for eligible papers) and maps output to ExtractionResult.
"""

import json
import logging
from typing import List

from src.config import PROMPTS_DIR, RAW_OUTPUTS_DIR, PROMPT_VERSION
from src.models.schemas import ExtractionResult, ClassificationResult
from src.services.llm_client import LLMClient
from src.utils.file_utils import read_prompt, write_json
from src.utils.text_utils import truncate_to_tokens

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = PROMPTS_DIR / "extraction_prompt.txt"
EXTRACTION_TEXT_TOKENS = 90_000


def extract_paper(
    paper_id: str,
    full_text: str,
    classification: ClassificationResult,
    client: LLMClient,
    save_raw: bool = True,
) -> List[ExtractionResult]:
    """
    Extract variables from one eligible paper.
    Returns a list of ExtractionResult (one per study).
    """
    system = read_prompt(SYSTEM_PROMPT_PATH)
    truncated = truncate_to_tokens(full_text, EXTRACTION_TEXT_TOKENS)
    context = (
        f"Paper ID: {paper_id}\n"
        f"Title: {classification.title}\n"
        f"Authors: {classification.authors}\n"
        f"Year: {classification.year}\n"
        f"Journal: {classification.journal}\n\n"
        f"---BEGIN PAPER---\n{truncated}\n---END PAPER---"
    )

    raw = client.complete(system=system, user=context)

    try:
        data = _safe_parse(raw)
    except ValueError as exc:
        logger.warning(f"[extractor] JSON parse failed for {paper_id}; retrying.")
        retry_msg = context + f"\n\nPrevious JSON parse error: {exc}. Return ONLY valid JSON."
        raw = client.complete(system=system, user=retry_msg)
        data = _safe_parse(raw)

    if save_raw:
        write_json(
            {"paper_id": paper_id, "step": "extraction",
             "prompt_version": PROMPT_VERSION, "response": data},
            RAW_OUTPUTS_DIR / f"{paper_id}_extraction.json"
        )

    studies = data.get("studies", [data])  # handle single-study responses
    results = []
    for i, study in enumerate(studies, start=1):
        suffix = study.get("study_suffix", f"S{i}") if len(studies) > 1 else "S1"
        study_id = f"{paper_id}-{suffix}" if len(studies) > 1 else paper_id
        er = _build_extraction_result(paper_id, study_id, classification, study)
        results.append(er)

    return results


def _safe_parse(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def _build_extraction_result(
    base_id: str,
    study_id: str,
    cls: ClassificationResult,
    data: dict,
) -> ExtractionResult:
    """Map raw LLM dict to ExtractionResult, filling paper-level fields from classification."""
    # Helper: coerce to int or None
    def _int(v):
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    def _float(v, default=0.5):
        try:
            return float(v) if v is not None else default
        except (TypeError, ValueError):
            return default

    def _bool_flag(v):
        """Convert 0/1/true/false to int 0 or 1."""
        if isinstance(v, bool):
            return 1 if v else 0
        try:
            return int(v) if v is not None else 0
        except (TypeError, ValueError):
            return 0

    return ExtractionResult(
        paper_id=study_id,
        base_paper_id=base_id,
        authors=cls.authors,
        year=cls.year,
        journal=cls.journal,
        title=cls.title,
        rq_summary=data.get("rq_summary"),
        num_hypotheses=_int(data.get("num_hypotheses")),
        primary_relationship=data.get("primary_relationship"),
        relationship_direction=_int(data.get("relationship_direction")),
        dv_name=data.get("dv_name"),
        dv_construct=data.get("dv_construct"),
        dv_measurement=data.get("dv_measurement"),
        dv_measurement_page=data.get("dv_measurement_page"),
        dv_source=_int(data.get("dv_source")),
        dv_type=_int(data.get("dv_type")),
        dv_num=_int(data.get("dv_num")),
        iv_name=data.get("iv_name"),
        iv_construct=data.get("iv_construct"),
        iv_measurement=data.get("iv_measurement"),
        iv_measurement_page=data.get("iv_measurement_page"),
        iv_source=_int(data.get("iv_source")),
        iv_type=_int(data.get("iv_type")),
        iv_num=_int(data.get("iv_num")),
        mediator_present=_bool_flag(data.get("mediator_present", 0)),
        mediator_name=data.get("mediator_name"),
        mediator_construct=data.get("mediator_construct"),
        mediator_measurement=data.get("mediator_measurement"),
        mediation_method=_int(data.get("mediation_method")),
        moderator_present=_bool_flag(data.get("moderator_present", 0)),
        moderator_name=data.get("moderator_name"),
        moderator_construct=data.get("moderator_construct"),
        moderator_measurement=data.get("moderator_measurement"),
        moderation_method=_int(data.get("moderation_method")),
        control_num=_int(data.get("control_num")),
        control_list=data.get("control_list"),
        control_justified=_int(data.get("control_justified")),
        sample_size=_int(data.get("sample_size")),
        sample_context=data.get("sample_context"),
        data_type=_int(data.get("data_type")),
        data_source_primary=data.get("data_source_primary"),
        unit_of_analysis=_int(data.get("unit_of_analysis")),
        time_period=data.get("time_period"),
        model_type=_int(data.get("model_type")),
        model_type_other=data.get("model_type_other"),
        endogeneity_addressed=_bool_flag(data.get("endogeneity_addressed", 0)),
        endogeneity_method=_int(data.get("endogeneity_method")),
        robustness_checks=_int(data.get("robustness_checks")),
        missing_mentioned=_bool_flag(data.get("missing_mentioned", 0)),
        missing_rate_reported=_bool_flag(data.get("missing_rate_reported", 0)),
        missing_rate_value=data.get("missing_rate_value"),
        missing_variables=data.get("missing_variables"),
        missing_handling=_int(data.get("missing_handling")),
        missing_handling_other=data.get("missing_handling_other"),
        missing_handling_page=data.get("missing_handling_page"),
        missing_justified=_bool_flag(data.get("missing_justified", 0)),
        missing_pattern_tested=_bool_flag(data.get("missing_pattern_tested", 0)),
        missing_pattern_result=_int(data.get("missing_pattern_result")),
        missing_sensitivity=_bool_flag(data.get("missing_sensitivity", 0)),
        data_available=_bool_flag(data.get("data_available", 0)),
        code_available=_bool_flag(data.get("code_available", 0)),
        software_reported=_bool_flag(data.get("software_reported", 0)),
        software_name=data.get("software_name"),
        replication_feasibility=_int(data.get("replication_feasibility")),
        confidence=_float(data.get("confidence"), 0.5),
        needs_review=bool(data.get("needs_review", False)),
        flag_reason=data.get("flag_reason"),
        coding_notes=data.get("coding_notes"),
    )
