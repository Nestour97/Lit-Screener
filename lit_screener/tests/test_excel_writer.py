"""Tests for Excel output writer."""

import pytest
from pathlib import Path
import pandas as pd

from src.models.schemas import ClassificationResult, ExtractionResult, LogEntry


def _make_cls(pid="paper_001"):
    return ClassificationResult(
        paper_id=pid,
        title="Test Paper on CEO Hubris",
        authors="Smith, Jones",
        year=2022,
        journal="SMJ",
        classification="Empirical Quantitative (Regression-based)",
        eligible_for_full_extraction=True,
        confidence=0.92,
        needs_review=False,
        rationale="Clear regression study.",
    )


def _make_ext(pid="paper_001"):
    return ExtractionResult(
        paper_id=pid,
        base_paper_id="paper_001",
        title="Test Paper on CEO Hubris",
        authors="Smith, Jones",
        year=2022,
        journal="SMJ",
        dv_name="Acquisition performance",
        iv_name="CEO hubris",
        model_type=1,
        missing_handling=1,
        missing_mentioned=1,
        sample_size=450,
        confidence=0.90,
    )


def _make_log(pid="001"):
    return LogEntry(
        paper_id=pid,
        step="extraction",
        level="info",
        message="Extracted successfully",
    )


def test_workbook_created(tmp_path):
    from src.services.excel_writer import write_workbook
    wb_path = tmp_path / "test_output.xlsx"
    write_workbook(
        input_files=["data/pdfs/001.pdf"],
        classifications=[_make_cls()],
        extractions=[_make_ext()],
        log_entries=[_make_log()],
        summary_md="## Summary\n\nThis is a test summary.",
        output_path=wb_path,
        stats={
            "total_papers": 1,
            "eligible_count": 1,
            "needs_review_count": 0,
            "extractions_count": 1,
            "by_category": {"Empirical Quantitative (Regression-based)": 1},
            "model_type_distribution": {"OLS": 1},
            "missing_handling_distribution": {"Listwise": 1},
            "missing_mentioned_pct": 100.0,
            "missing_rate_reported_pct": 0.0,
            "missing_justified_pct": 0.0,
            "replication_feasibility": {"NR": 1},
        }
    )
    assert wb_path.exists()

    # Verify all expected sheets exist
    xl = pd.ExcelFile(str(wb_path))
    assert "Input" in xl.sheet_names
    assert "Classification" in xl.sheet_names
    assert "Extraction" in xl.sheet_names
    assert "Log" in xl.sheet_names
    assert "Summary" in xl.sheet_names


def test_extraction_sheet_columns(tmp_path):
    from src.services.excel_writer import write_workbook
    wb_path = tmp_path / "test_cols.xlsx"
    write_workbook(
        input_files=["data/pdfs/001.pdf"],
        classifications=[_make_cls()],
        extractions=[_make_ext()],
        log_entries=[],
        summary_md=None,
        output_path=wb_path,
        stats=None,
    )
    df = pd.read_excel(str(wb_path), sheet_name="Extraction")
    # Check key columns exist
    for col in ["Paper_ID", "DV_Name", "IV_Name", "Model_Type",
                 "Missing_Handling", "Missing_Mentioned", "Confidence"]:
        assert col in df.columns, f"Missing column: {col}"

    # Check data
    assert str(df.iloc[0]["Paper_ID"]) == "paper_001"
    assert df.iloc[0]["Model_Type"] == "OLS"
    assert df.iloc[0]["Missing_Handling"] == "Listwise"


def test_needs_review_row(tmp_path):
    from src.services.excel_writer import write_workbook
    ext = _make_ext()
    ext.needs_review = True
    ext.flag_reason = "Ambiguous IV measurement"
    wb_path = tmp_path / "test_review.xlsx"
    write_workbook(
        input_files=["data/pdfs/001.pdf"],
        classifications=[_make_cls()],
        extractions=[ext],
        log_entries=[],
        summary_md=None,
        output_path=wb_path,
        stats=None,
    )
    df = pd.read_excel(str(wb_path), sheet_name="Extraction")
    assert df.iloc[0]["Needs_Review"] == "Yes"
    assert "Ambiguous" in df.iloc[0]["Flag_Reason"]
