"""Tests for Pydantic schema validation."""

import pytest
from src.models.schemas import ClassificationResult, ExtractionResult, LogEntry


def test_classification_result_valid():
    c = ClassificationResult(
        paper_id="001",
        title="Test Paper",
        classification="Empirical Quantitative (Regression-based)",
        eligible_for_full_extraction=True,
        confidence=0.95,
    )
    assert c.paper_id == "001"
    assert c.eligible_for_full_extraction is True
    assert c.confidence == 0.95


def test_classification_confidence_bounds():
    with pytest.raises(Exception):
        ClassificationResult(
            paper_id="001",
            classification="Empirical Quantitative (Regression-based)",
            eligible_for_full_extraction=True,
            confidence=1.5,   # out of range
        )


def test_extraction_result_defaults():
    e = ExtractionResult(paper_id="001-S1", base_paper_id="001")
    assert e.mediator_present == 0
    assert e.moderator_present == 0
    assert e.missing_mentioned == 0
    assert e.confidence == 0.5
    assert e.needs_review is False


def test_extraction_result_full():
    e = ExtractionResult(
        paper_id="002",
        base_paper_id="002",
        title="CEO Hubris and Acquisitions",
        authors="Smith, Jones",
        year=2022,
        journal="SMJ",
        dv_name="Acquisition performance",
        iv_name="CEO hubris",
        model_type=1,   # OLS
        missing_handling=1,  # Listwise
        missing_mentioned=1,
        sample_size=450,
        confidence=0.87,
        needs_review=False,
    )
    assert e.model_type == 1
    assert e.missing_handling == 1
    assert e.sample_size == 450


def test_log_entry():
    entry = LogEntry(
        paper_id="003",
        step="extraction",
        level="flag",
        message="Ambiguous mediator role",
        page_reference="p. 14",
    )
    assert entry.level == "flag"
    assert entry.page_reference == "p. 14"
