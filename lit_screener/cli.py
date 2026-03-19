"""
CLI entry point for batch runs.

Usage examples:
  python cli.py --pdf-dir data/pdfs --classify-only
  python cli.py --pdf-dir data/pdfs
  python cli.py --csv paper_links.csv
  python cli.py --pdf-dir data/pdfs --rerun 003 007
"""

import sys
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config import DATA_DIR, OUTPUTS_DIR
from src.services.llm_client import LLMClient
from src.services.drive_loader import load_papers_from_csv
from src.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUTPUTS_DIR / "cli_run.log"),
    ]
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="LLM Literature Screener — CLI batch runner"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--pdf-dir", type=Path,
                        help="Directory containing local PDF files")
    source.add_argument("--csv", type=Path,
                        help="CSV/XLSX with columns: paper_id, url (Google Drive links)")

    parser.add_argument("--classify-only", action="store_true",
                        help="Run classification only (skip extraction)")
    parser.add_argument("--output-dir", type=Path, default=OUTPUTS_DIR,
                        help="Output directory (default: outputs/)")
    parser.add_argument("--provider", default=None,
                        help="LLM provider: openai | anthropic (overrides env LLM_PROVIDER)")
    parser.add_argument("--model", default=None,
                        help="Model name (overrides env OPENAI_MODEL / ANTHROPIC_MODEL)")
    parser.add_argument("--rerun", nargs="+", metavar="PAPER_ID",
                        help="Only reprocess these paper IDs")

    args = parser.parse_args()

    # ── Resolve PDF paths ─────────────────────────────────────────────────────
    if args.pdf_dir:
        pdf_paths = sorted(args.pdf_dir.glob("*.pdf"))
        if not pdf_paths:
            logger.error(f"No PDFs found in {args.pdf_dir}")
            sys.exit(1)
    else:
        logger.info(f"Loading papers from CSV: {args.csv}")
        dest_dir = DATA_DIR / "pdfs"
        drive_results = load_papers_from_csv(args.csv, dest_dir)
        pdf_paths = [p for p in drive_results.values() if p and p.exists()]
        if not pdf_paths:
            logger.error("No papers successfully downloaded.")
            sys.exit(1)

    logger.info(f"Papers to process: {len(pdf_paths)}")

    # ── Build client ──────────────────────────────────────────────────────────
    client = LLMClient(provider=args.provider, model=args.model)
    logger.info(f"LLM: {client.provider} / {client.model}")

    # ── Run ───────────────────────────────────────────────────────────────────
    def cli_progress(paper_id, message, progress):
        pct = int(progress * 100)
        logger.info(f"[{pct:3d}%] [{paper_id}] {message}")

    results = run_pipeline(
        pdf_paths=pdf_paths,
        client=client,
        run_extraction=not args.classify_only,
        output_dir=args.output_dir,
        progress_cb=cli_progress,
        rerun_ids=args.rerun,
    )

    # ── Print summary ─────────────────────────────────────────────────────────
    stats = results["stats"]
    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)
    print(f"Total papers:       {stats['total_papers']}")
    print(f"Eligible:           {stats['eligible_count']}")
    print(f"Extractions:        {stats['extractions_count']}")
    print(f"Needs review:       {stats['needs_review_count']}")
    print(f"Workbook:           {results['workbook_path']}")
    print(f"Report:             {args.output_dir / 'reports' / 'summary_report.md'}")
    print("="*60)


if __name__ == "__main__":
    main()
