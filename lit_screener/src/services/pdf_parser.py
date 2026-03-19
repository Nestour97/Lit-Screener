"""
PDF parsing service.
Primary parser: PyMuPDF (fitz) — page-aware extraction.
Fallback: pdfplumber.
Results are cached as plain text files.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


@dataclass
class PageText:
    page_num: int       # 1-indexed
    text: str


@dataclass
class ParsedPDF:
    path: Path
    pages: List[PageText] = field(default_factory=list)
    full_text: str = ""
    error: Optional[str] = None

    def get_page(self, num: int) -> Optional[str]:
        for p in self.pages:
            if p.page_num == num:
                return p.text
        return None


def parse_pdf(pdf_path: Path, cache_dir: Optional[Path] = None) -> ParsedPDF:
    """
    Extract text from a PDF, caching result as .txt beside the PDF or in cache_dir.
    Returns a ParsedPDF with per-page text.
    """
    pdf_path = Path(pdf_path)
    cache_path = _cache_path(pdf_path, cache_dir)

    if cache_path and cache_path.exists():
        logger.info(f"[pdf_parser] Using cached text for {pdf_path.name}")
        return _load_from_cache(pdf_path, cache_path)

    result = _parse_with_pymupdf(pdf_path)
    if result.error:
        logger.warning(f"[pdf_parser] PyMuPDF failed for {pdf_path.name}: {result.error}. Trying pdfplumber.")
        result = _parse_with_pdfplumber(pdf_path)

    if cache_path and not result.error:
        _save_to_cache(result, cache_path)

    return result


def _cache_path(pdf_path: Path, cache_dir: Optional[Path]) -> Optional[Path]:
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / (pdf_path.stem + ".txt")
    return None


def _parse_with_pymupdf(pdf_path: Path) -> ParsedPDF:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return ParsedPDF(path=pdf_path, error="PyMuPDF not installed")

    pages = []
    try:
        doc = fitz.open(str(pdf_path))
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")
            pages.append(PageText(page_num=i, text=text))
        doc.close()
    except Exception as exc:
        return ParsedPDF(path=pdf_path, error=str(exc))

    full_text = "\n\n".join(
        f"[PAGE {p.page_num}]\n{p.text}" for p in pages
    )
    return ParsedPDF(path=pdf_path, pages=pages, full_text=full_text)


def _parse_with_pdfplumber(pdf_path: Path) -> ParsedPDF:
    try:
        import pdfplumber
    except ImportError:
        return ParsedPDF(path=pdf_path, error="pdfplumber not installed")

    pages = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append(PageText(page_num=i, text=text))
    except Exception as exc:
        return ParsedPDF(path=pdf_path, error=str(exc))

    full_text = "\n\n".join(
        f"[PAGE {p.page_num}]\n{p.text}" for p in pages
    )
    return ParsedPDF(path=pdf_path, pages=pages, full_text=full_text)


def _save_to_cache(result: ParsedPDF, cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(result.full_text)


def _load_from_cache(pdf_path: Path, cache_path: Path) -> ParsedPDF:
    with open(cache_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    # Re-split into pages from the [PAGE N] markers
    import re
    segments = re.split(r"\[PAGE (\d+)\]\n", full_text)
    pages = []
    i = 1
    while i < len(segments):
        page_num = int(segments[i])
        text = segments[i + 1] if i + 1 < len(segments) else ""
        pages.append(PageText(page_num=page_num, text=text))
        i += 2

    return ParsedPDF(path=pdf_path, pages=pages, full_text=full_text)
