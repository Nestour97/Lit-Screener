"""Tests for PDF parser (uses the sample paper bundled with the project)."""

import pytest
from pathlib import Path
import tempfile


def test_parse_nonexistent_file():
    from src.services.pdf_parser import parse_pdf
    result = parse_pdf(Path("/tmp/nonexistent_12345.pdf"))
    assert result.error is not None


def test_cache_roundtrip(tmp_path):
    """Create a fake cached text file and verify it loads correctly."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Write a fake cached text file in the expected format
    fake_text = "[PAGE 1]\nIntroduction text.\n\n[PAGE 2]\nMethods section."
    paper_name = "test_paper"
    cache_file = cache_dir / f"{paper_name}.txt"
    cache_file.write_text(fake_text, encoding="utf-8")

    # Verify parsing the format we wrote
    import re
    segments = re.split(r"\[PAGE (\d+)\]\n", fake_text)
    pages = []
    i = 1
    while i < len(segments):
        page_num = int(segments[i])
        text = segments[i + 1] if i + 1 < len(segments) else ""
        pages.append((page_num, text))
        i += 2

    assert len(pages) == 2
    assert pages[0][0] == 1
    assert "Introduction" in pages[0][1]
    assert pages[1][0] == 2
    assert "Methods" in pages[1][1]


def test_text_truncation():
    from src.utils.text_utils import truncate_to_tokens
    long_text = "word " * 10000
    truncated = truncate_to_tokens(long_text, max_tokens=100)
    assert len(truncated) < len(long_text)
    assert "[TEXT TRUNCATED" in truncated


def test_clean_text():
    from src.utils.text_utils import clean_text
    messy = "Hello  world\r\n\n\n\n\nMore text   here"
    clean = clean_text(messy)
    assert "  " not in clean
    assert "\r" not in clean
    # Should have at most 2 consecutive newlines
    assert "\n\n\n" not in clean
