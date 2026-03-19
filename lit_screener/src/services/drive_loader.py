"""
Google Drive loader.
Downloads PDFs from public share links.

Limitations / Assumptions:
- Only works with publicly accessible links (no OAuth required).
- For private Google Drive files, you must download manually and place in data/pdfs/.
- Supported link formats:
    https://drive.google.com/file/d/{FILE_ID}/view
    https://drive.google.com/open?id={FILE_ID}
    https://drive.google.com/uc?id={FILE_ID}

Fallback: if download fails (private or restricted), a warning is logged and the
file is skipped. Place the PDF manually in data/pdfs/{paper_id}.pdf.
"""

import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DRIVE_FILE_RE = re.compile(
    r"(?:drive\.google\.com/file/d/|drive\.google\.com/open\?id=|drive\.google\.com/uc\?id=)"
    r"([A-Za-z0-9_\-]+)"
)


def extract_file_id(url: str) -> Optional[str]:
    m = _DRIVE_FILE_RE.search(url)
    return m.group(1) if m else None


def download_drive_file(url: str, dest_path: Path, timeout: int = 60) -> bool:
    """
    Attempt to download a Google Drive file to dest_path.
    Returns True on success, False on failure.
    """
    file_id = extract_file_id(url)
    if not file_id:
        logger.warning(f"[drive_loader] Cannot parse file ID from URL: {url}")
        return False

    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        import requests
        session = requests.Session()
        resp = session.get(download_url, stream=True, timeout=timeout)

        # Handle Google Drive's virus-scan confirmation page
        token = _get_confirm_token(resp)
        if token:
            params = {"confirm": token, "id": file_id}
            resp = session.get(
                "https://drive.google.com/uc?export=download",
                params=params, stream=True, timeout=timeout
            )

        if resp.status_code != 200:
            logger.warning(f"[drive_loader] HTTP {resp.status_code} for {url}")
            return False

        content_type = resp.headers.get("Content-Type", "")
        if "html" in content_type and b"%PDF" not in resp.content[:10]:
            logger.warning(
                f"[drive_loader] Received HTML instead of PDF for {url}. "
                "File may be private. Please download manually."
            )
            return False

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=32768):
                if chunk:
                    f.write(chunk)

        logger.info(f"[drive_loader] Downloaded {dest_path.name} ({dest_path.stat().st_size} bytes)")
        return True

    except Exception as exc:
        logger.error(f"[drive_loader] Download failed for {url}: {exc}")
        return False


def _get_confirm_token(response) -> Optional[str]:
    """Extract the virus-scan confirmation token from a Drive response."""
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value
    return None


def load_papers_from_csv(csv_path: Path, dest_dir: Path) -> dict:
    """
    Load a CSV with columns [paper_id, url] (or [Paper_ID, URL]).
    Downloads each file to dest_dir/{paper_id}.pdf.
    Returns {paper_id: local_pdf_path or None}.
    """
    import pandas as pd
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.lower().str.strip()

    if "paper_id" not in df.columns or "url" not in df.columns:
        raise ValueError("CSV must have columns: paper_id, url")

    results = {}
    for _, row in df.iterrows():
        pid = str(row["paper_id"]).strip()
        url = str(row["url"]).strip()
        dest = dest_dir / f"{pid}.pdf"

        if dest.exists():
            logger.info(f"[drive_loader] {pid}: already downloaded, skipping.")
            results[pid] = dest
        else:
            ok = download_drive_file(url, dest)
            results[pid] = dest if ok else None

    return results
