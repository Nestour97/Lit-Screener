"""
Core pipeline orchestrator.
Provides run_pipeline() which is called by both app.py and cli.py.
"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from src.config import OUTPUTS_DIR, NORMALIZED_TEXT_DIR, REPORTS_DIR
from src.models.schemas import PaperRecord, ClassificationResult, ExtractionResult, LogEntry
from src.services.pdf_parser import parse_pdf
from src.services.llm_client import LLMClient
from src.services.classifier import classify_paper
from src.services.extractor import extract_paper
from src.services.summarizer import generate_summary_report, compute_stats
from src.services.excel_writer import write_workbook
from src.services.logger import ExtractionLogger
from src.utils.text_utils import clean_text

logger = logging.getLogger(__name__)

PipelineCallback = Callable[[str, str, float], None]   # (paper_id, message, progress 0-1)


def run_pipeline(
    pdf_paths: List[Path],
    client: LLMClient,
    run_extraction: bool = True,
    output_dir: Path = None,
    progress_cb: Optional[PipelineCallback] = None,
    rerun_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Main pipeline entry point.

    Args:
        pdf_paths: List of PDF files to process.
        client: Initialised LLMClient.
        run_extraction: If False, only run classification.
        output_dir: Where to write outputs (defaults to OUTPUTS_DIR).
        progress_cb: Optional callback(paper_id, message, 0-1) for UI.
        rerun_ids: If set, only reprocess these paper IDs.

    Returns:
        Dict with keys: records, classifications, extractions, log_entries,
                        workbook_path, summary_md, stats.
    """
    output_dir = output_dir or OUTPUTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = output_dir / "extraction_log.jsonl"
    ext_logger = ExtractionLogger(jsonl_path)
    records: List[PaperRecord] = []
    classifications: List[ClassificationResult] = []
    extractions: List[ExtractionResult] = []

    total = len(pdf_paths)

    for idx, pdf_path in enumerate(pdf_paths):
        paper_id = pdf_path.stem
        if rerun_ids and paper_id not in rerun_ids:
            continue

        progress = idx / total
        _cb(progress_cb, paper_id, f"Parsing PDF ({idx+1}/{total})…", progress)
        ext_logger.info(paper_id, "parsing", f"Starting: {pdf_path.name}")

        # ── 1. Parse PDF ──────────────────────────────────────────────────────
        t0 = time.time()
        parsed = parse_pdf(pdf_path, cache_dir=NORMALIZED_TEXT_DIR)
        if parsed.error:
            ext_logger.error(paper_id, "parsing", f"PDF parse failed: {parsed.error}")
            records.append(PaperRecord(paper_id=paper_id, filename=pdf_path.name, status="failed"))
            continue

        full_text = clean_text(parsed.full_text)
        record = PaperRecord(paper_id=paper_id, filename=pdf_path.name,
                              text_path=str(NORMALIZED_TEXT_DIR / f"{paper_id}.txt"))

        # ── 2. Classify ───────────────────────────────────────────────────────
        _cb(progress_cb, paper_id, "Classifying…", progress + 0.3 / total)
        try:
            cls = classify_paper(paper_id, full_text, client)
            record.classification = cls
            classifications.append(cls)
            ext_logger.info(paper_id, "classification",
                            f"→ {cls.classification} | eligible={cls.eligible_for_full_extraction} | conf={cls.confidence:.2f}")
            if cls.needs_review:
                ext_logger.flag(paper_id, "classification", f"Needs review: {cls.flag_reason}")
        except Exception as exc:
            ext_logger.error(paper_id, "classification", str(exc))
            record.status = "failed"
            records.append(record)
            continue

        # ── 3. Extract (if eligible) ──────────────────────────────────────────
        if run_extraction and cls.eligible_for_full_extraction:
            _cb(progress_cb, paper_id, "Extracting variables…", progress + 0.6 / total)
            try:
                paper_extractions = extract_paper(paper_id, full_text, cls, client)
                record.extractions = paper_extractions
                extractions.extend(paper_extractions)
                ext_logger.info(paper_id, "extraction",
                                f"Extracted {len(paper_extractions)} study record(s)")
                for ex in paper_extractions:
                    if ex.needs_review:
                        ext_logger.flag(paper_id, "extraction", f"[{ex.paper_id}] {ex.flag_reason}")
            except Exception as exc:
                ext_logger.error(paper_id, "extraction", str(exc))
                record.status = "needs_review"
                record.log_entries.append(LogEntry(
                    paper_id=paper_id, step="extraction", level="error",
                    message=str(exc)
                ))
        elif not cls.eligible_for_full_extraction:
            ext_logger.info(paper_id, "extraction", "Skipped (not eligible).")

        record.status = "processed"
        record.processing_time_s = time.time() - t0
        record.log_entries.extend([e for e in ext_logger.entries if e.paper_id == paper_id])
        records.append(record)
        _cb(progress_cb, paper_id, "Done.", (idx + 1) / total)

    # ── 4. Summary report ────────────────────────────────────────────────────
    _cb(progress_cb, "ALL", "Generating summary report…", 0.95)
    summary_md = ""
    stats = compute_stats(classifications, extractions)
    try:
        summary_md = generate_summary_report(classifications, extractions, client)
    except Exception as exc:
        logger.error(f"[pipeline] Summary report failed: {exc}")

    # ── 5. Write workbook ────────────────────────────────────────────────────
    _cb(progress_cb, "ALL", "Writing Excel workbook…", 0.98)
    workbook_path = output_dir / "extraction_output.xlsx"
    write_workbook(
        input_files=[str(p) for p in pdf_paths],
        classifications=classifications,
        extractions=extractions,
        log_entries=ext_logger.entries,
        summary_md=summary_md,
        output_path=workbook_path,
        stats=stats,
    )

    # ── 6. Write classification framework doc ─────────────────────────────────
    _write_classification_framework()

    _cb(progress_cb, "ALL", "Pipeline complete.", 1.0)

    return {
        "records": records,
        "classifications": classifications,
        "extractions": extractions,
        "log_entries": ext_logger.entries,
        "workbook_path": workbook_path,
        "summary_md": summary_md,
        "stats": stats,
    }


def _cb(fn, paper_id, message, progress):
    if fn:
        try:
            fn(paper_id, message, progress)
        except Exception:
            pass


def _write_classification_framework():
    """Write the classification framework document to reports/."""
    path = REPORTS_DIR / "classification_framework.md"
    content = """\
# Classification Framework

Version: v1.0 | Study: Missing Data Handling Practices

## Categories

| # | Category | Eligible | Criteria |
|---|----------|----------|----------|
| 1 | **Empirical Quantitative (Regression-based)** | ✅ Yes | Quantitative data, regression as primary method, management topic |
| 2 | Empirical Qualitative | ❌ No | Interviews, ethnography, case studies without regression |
| 3 | Empirical Mixed Methods | ❌ No | Qualitative + quantitative but regression not primary; flag for review |
| 4 | Review / Meta-analysis | ❌ No | Systematic reviews, meta-analyses |
| 5 | Theoretical / Conceptual | ❌ No | No original empirical data |
| 6 | Non-management / Out of Scope | ❌ No | Outside management/OB/strategy or purely methodological |
| 7 | Other | ❌ No | Always set needs_review=true |

## Borderline Rules
- If ANY quantitative regression analysis exists → prefer Empirical Quantitative
- Confidence < 0.60 → automatic needs_review = true
- When in doubt between categories → flag for human review

## Confidence Rating
- **High (≥ 0.80):** Clear evidence; coder is certain
- **Medium (0.60–0.79):** Some ambiguity; best interpretation applied
- **Low (< 0.60):** Substantial uncertainty; human review required
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
