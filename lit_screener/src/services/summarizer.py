"""
Summary report generator.
Computes descriptive statistics from extraction results and generates a Markdown report.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

from src.config import PROMPTS_DIR, REPORTS_DIR, PROMPT_VERSION
from src.models.schemas import ClassificationResult, ExtractionResult
from src.services.llm_client import LLMClient
from src.utils.file_utils import read_prompt

logger = logging.getLogger(__name__)

MODEL_TYPE_LABELS = {
    1: "OLS", 2: "Logit/Probit", 3: "FE", 4: "RE", 5: "GLS",
    6: "GMM", 7: "HLM", 8: "SEM", 9: "Count", 10: "Heckman", 11: "Other"
}
MISSING_LABELS = {
    1: "Listwise", 2: "Pairwise", 3: "Mean substitution",
    4: "Regression imputation", 5: "Multiple imputation (MI)",
    6: "FIML", 7: "EM", 8: "Hot-deck", 9: "NR", 10: "Other"
}


def compute_stats(
    classifications: List[ClassificationResult],
    extractions: List[ExtractionResult],
) -> Dict[str, Any]:
    """Compute descriptive statistics for the summary report."""
    total = len(classifications)
    by_category: Dict[str, int] = {}
    for c in classifications:
        by_category[c.classification] = by_category.get(c.classification, 0) + 1

    eligible = [c for c in classifications if c.eligible_for_full_extraction]
    needs_review = [c for c in classifications if c.needs_review]

    n_ext = len(extractions)

    # Model types
    model_counts: Dict[str, int] = {}
    for e in extractions:
        label = MODEL_TYPE_LABELS.get(e.model_type, "NR") if e.model_type else "NR"
        model_counts[label] = model_counts.get(label, 0) + 1

    # Missing handling
    missing_counts: Dict[str, int] = {}
    for e in extractions:
        label = MISSING_LABELS.get(e.missing_handling, "NR") if e.missing_handling else "NR"
        missing_counts[label] = missing_counts.get(label, 0) + 1

    # Missing reporting rates
    missing_mentioned_pct = (
        sum(1 for e in extractions if e.missing_mentioned) / n_ext * 100
        if n_ext else 0
    )
    missing_rate_reported_pct = (
        sum(1 for e in extractions if e.missing_rate_reported) / n_ext * 100
        if n_ext else 0
    )
    missing_justified_pct = (
        sum(1 for e in extractions if e.missing_justified) / n_ext * 100
        if n_ext else 0
    )

    # Replication feasibility
    rep_counts: Dict[str, int] = {
        "High": 0, "Medium": 0, "Low": 0, "Not feasible": 0, "NR": 0
    }
    rep_map = {1: "High", 2: "Medium", 3: "Low", 4: "Not feasible"}
    for e in extractions:
        label = rep_map.get(e.replication_feasibility, "NR") if e.replication_feasibility else "NR"
        rep_counts[label] = rep_counts.get(label, 0) + 1

    return {
        "total_papers": total,
        "by_category": by_category,
        "eligible_count": len(eligible),
        "needs_review_count": len(needs_review),
        "extractions_count": n_ext,
        "model_type_distribution": model_counts,
        "missing_handling_distribution": missing_counts,
        "missing_mentioned_pct": round(missing_mentioned_pct, 1),
        "missing_rate_reported_pct": round(missing_rate_reported_pct, 1),
        "missing_justified_pct": round(missing_justified_pct, 1),
        "replication_feasibility": rep_counts,
    }


def generate_summary_report(
    classifications: List[ClassificationResult],
    extractions: List[ExtractionResult],
    client: LLMClient,
    output_path: Path = None,
) -> str:
    """Generate a 500-800 word Markdown summary report via LLM."""
    stats = compute_stats(classifications, extractions)
    system = read_prompt(PROMPTS_DIR / "summary_prompt.txt")

    import json
    sample_extractions = [
        {k: v for k, v in e.dict().items()
         if k in ("paper_id", "model_type", "missing_handling", "missing_mentioned",
                   "missing_justified", "replication_feasibility", "dv_name", "iv_name")}
        for e in extractions[:10]
    ]

    user_msg = f"""
Here is the data for your summary:

## Statistics
{json.dumps(stats, indent=2)}

## Sample Extraction Rows (first 10)
{json.dumps(sample_extractions, indent=2)}
"""
    report_md = client.complete(
        system=system, user=user_msg, max_tokens=1500
    )

    if output_path is None:
        output_path = REPORTS_DIR / "summary_report.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    logger.info(f"[summarizer] Report written to {output_path}")
    return report_md
