"""Text preprocessing utilities."""

import re


def clean_text(text: str) -> str:
    """Basic clean-up: normalise whitespace, remove control chars."""
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate_to_tokens(text: str, max_tokens: int, chars_per_token: float = 4.0) -> str:
    """Rough truncation: 1 token ≈ 4 chars. Cuts at last paragraph boundary."""
    max_chars = int(max_tokens * chars_per_token)
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    # Find last paragraph break to avoid mid-sentence cuts
    last_break = truncated.rfind("\n\n")
    if last_break > max_chars // 2:
        truncated = truncated[:last_break]
    return truncated + "\n\n[TEXT TRUNCATED FOR LENGTH]"


def na_or_nr(value, applicable: bool = True) -> str:
    """Return 'NA' or 'NR' when a value is missing."""
    if value is None or value == "":
        return "NA" if not applicable else "NR"
    return str(value)
