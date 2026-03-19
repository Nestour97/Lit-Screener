"""
Pydantic schemas for all structured outputs.
These are the ground-truth data models used throughout the pipeline.

Assumptions documented here:
- confidence is a float 0-1 (not a 3-level enum) for finer granularity;
  maps to ConfidenceLevel for display: >=0.8=High, >=0.5=Medium, else Low.
- Optional fields default to None; downstream code converts None → "NR" or "NA"
  per the coding guidelines.
- multi-study papers use Paper_ID suffix e.g. "001-S1", "001-S2".
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field


# ── Classification Output ────────────────────────────────────────────────────

class ClassificationResult(BaseModel):
    """Output of the classification LLM call for one paper."""
    paper_id: str
    title: str = ""
    authors: str = ""
    year: Optional[int] = None
    journal: str = ""
    classification: str  # one of ClassificationCategory values
    eligible_for_full_extraction: bool
    confidence: float = Field(ge=0.0, le=1.0)
    needs_review: bool = False
    flag_reason: Optional[str] = None
    rationale: str = ""  # short explanation


# ── Extraction Output ────────────────────────────────────────────────────────

class ExtractionResult(BaseModel):
    """
    Full variable-extraction output for one study within one paper.
    All fields are Optional; None is serialised as "NR" or "NA" per context.
    """

    # ── Category 1: Paper Identification ────────────────────────────────────
    paper_id: str                      # e.g. "001" or "001-S2" for multi-study
    base_paper_id: str                 # always the plain paper id e.g. "001"
    authors: str = ""
    year: Optional[int] = None
    journal: str = ""
    title: str = ""

    # ── Category 2: Core Research Question ──────────────────────────────────
    rq_summary: Optional[str] = None
    num_hypotheses: Optional[int] = None
    primary_relationship: Optional[str] = None
    relationship_direction: Optional[int] = None  # 1-4 per enum

    # ── Category 3: Dependent Variable ──────────────────────────────────────
    dv_name: Optional[str] = None
    dv_construct: Optional[str] = None
    dv_measurement: Optional[str] = None
    dv_measurement_page: Optional[str] = None   # page number evidence
    dv_source: Optional[int] = None
    dv_type: Optional[int] = None
    dv_num: Optional[int] = None

    # ── Category 4: Independent Variable ────────────────────────────────────
    iv_name: Optional[str] = None
    iv_construct: Optional[str] = None
    iv_measurement: Optional[str] = None
    iv_measurement_page: Optional[str] = None
    iv_source: Optional[int] = None
    iv_type: Optional[int] = None
    iv_num: Optional[int] = None

    # ── Category 5: Mediation ────────────────────────────────────────────────
    mediator_present: int = 0           # 0 or 1
    mediator_name: Optional[str] = None
    mediator_construct: Optional[str] = None
    mediator_measurement: Optional[str] = None
    mediation_method: Optional[int] = None

    # ── Category 6: Moderation ───────────────────────────────────────────────
    moderator_present: int = 0
    moderator_name: Optional[str] = None
    moderator_construct: Optional[str] = None
    moderator_measurement: Optional[str] = None
    moderation_method: Optional[int] = None

    # ── Category 7: Controls ─────────────────────────────────────────────────
    control_num: Optional[int] = None
    control_list: Optional[str] = None
    control_justified: Optional[int] = None     # 0, 1, or 2

    # ── Category 8: Sample & Data ────────────────────────────────────────────
    sample_size: Optional[int] = None
    sample_context: Optional[str] = None
    data_type: Optional[int] = None
    data_source_primary: Optional[str] = None
    unit_of_analysis: Optional[int] = None
    time_period: Optional[str] = None

    # ── Category 9: Analytical Method ────────────────────────────────────────
    model_type: Optional[int] = None
    model_type_other: Optional[str] = None
    endogeneity_addressed: int = 0
    endogeneity_method: Optional[int] = None
    robustness_checks: Optional[int] = None

    # ── Category 10: Missing Data ─────────────────────────────────────────────
    missing_mentioned: int = 0
    missing_rate_reported: int = 0
    missing_rate_value: Optional[str] = None
    missing_variables: Optional[str] = None
    missing_handling: Optional[int] = None
    missing_handling_other: Optional[str] = None
    missing_handling_page: Optional[str] = None
    missing_justified: int = 0
    missing_pattern_tested: int = 0
    missing_pattern_result: Optional[int] = None
    missing_sensitivity: int = 0

    # ── Category 11: Replication ──────────────────────────────────────────────
    data_available: int = 0
    code_available: int = 0
    software_reported: int = 0
    software_name: Optional[str] = None
    replication_feasibility: Optional[int] = None

    # ── Meta / QC ─────────────────────────────────────────────────────────────
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    needs_review: bool = False
    flag_reason: Optional[str] = None
    coding_notes: Optional[str] = None


# ── Log Entry ────────────────────────────────────────────────────────────────

class LogEntry(BaseModel):
    """One row in the extraction log."""
    paper_id: str
    step: str                   # "classification" | "extraction" | "parsing"
    level: str                  # "info" | "warning" | "flag" | "error"
    message: str
    page_reference: Optional[str] = None
    timestamp: Optional[str] = None


# ── Paper Record ─────────────────────────────────────────────────────────────

class PaperRecord(BaseModel):
    """Internal record tracking the state of one paper through the pipeline."""
    paper_id: str
    filename: str
    status: str = "pending"
    text_path: Optional[str] = None          # path to cached plain text
    classification: Optional[ClassificationResult] = None
    extractions: List[ExtractionResult] = Field(default_factory=list)
    log_entries: List[LogEntry] = Field(default_factory=list)
    processing_time_s: Optional[float] = None
