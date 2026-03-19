"""Tests for Google Drive URL parsing."""

from src.services.drive_loader import extract_file_id


def test_extract_file_id_standard():
    url = "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWx/view?usp=sharing"
    assert extract_file_id(url) == "1AbCdEfGhIjKlMnOpQrStUvWx"


def test_extract_file_id_open():
    url = "https://drive.google.com/open?id=1AbCdEfGhIjKlMnOpQrStUvWx"
    assert extract_file_id(url) == "1AbCdEfGhIjKlMnOpQrStUvWx"


def test_extract_file_id_uc():
    url = "https://drive.google.com/uc?id=1AbCdEfGhIjKlMnOpQrStUvWx"
    assert extract_file_id(url) == "1AbCdEfGhIjKlMnOpQrStUvWx"


def test_extract_file_id_invalid():
    assert extract_file_id("https://example.com/notadrivefile") is None
    assert extract_file_id("") is None
