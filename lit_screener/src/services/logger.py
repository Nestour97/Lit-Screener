"""
Extraction logger: writes JSONL entries and provides a list of LogEntry objects.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from src.models.schemas import LogEntry

_logger = logging.getLogger(__name__)


class ExtractionLogger:
    """Accumulates LogEntry objects; can flush to JSONL."""

    def __init__(self, jsonl_path: Path):
        self.jsonl_path = jsonl_path
        self.entries: List[LogEntry] = []
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, paper_id: str, step: str, level: str, message: str,
            page_reference: str = None) -> LogEntry:
        entry = LogEntry(
            paper_id=paper_id,
            step=step,
            level=level,
            message=message,
            page_reference=page_reference,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.entries.append(entry)
        self._append_jsonl(entry)
        # Also emit to Python logging
        log_fn = {"info": _logger.info, "warning": _logger.warning,
                  "flag": _logger.warning, "error": _logger.error}.get(level, _logger.info)
        log_fn(f"[{paper_id}] {step}: {message}")
        return entry

    def info(self, paper_id, step, message, **kw):
        return self.log(paper_id, step, "info", message, **kw)

    def warning(self, paper_id, step, message, **kw):
        return self.log(paper_id, step, "warning", message, **kw)

    def flag(self, paper_id, step, message, **kw):
        return self.log(paper_id, step, "flag", message, **kw)

    def error(self, paper_id, step, message, **kw):
        return self.log(paper_id, step, "error", message, **kw)

    def _append_jsonl(self, entry: LogEntry) -> None:
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.dict(), default=str) + "\n")
