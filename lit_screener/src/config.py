"""
Central configuration. All values come from environment variables with safe defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"
RAW_OUTPUTS_DIR = OUTPUTS_DIR / "raw_model_outputs"
NORMALIZED_TEXT_DIR = OUTPUTS_DIR / "normalized_text"
REPORTS_DIR = OUTPUTS_DIR / "reports"
PROMPTS_DIR = BASE_DIR / "src" / "prompts"

for d in [DATA_DIR, DATA_DIR / "pdfs", OUTPUTS_DIR, RAW_OUTPUTS_DIR,
          NORMALIZED_TEXT_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── LLM Provider ─────────────────────────────────────────────────────────────

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")   # "openai" | "anthropic"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-6")

# Max tokens for extraction response (large papers need headroom)
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))

# ── PDF Parsing ───────────────────────────────────────────────────────────────

# Max pages to send to LLM to avoid context overflow; 0 = no limit
PDF_MAX_PAGES = int(os.getenv("PDF_MAX_PAGES", "0"))
# Approx token budget for paper text in the prompt
PDF_TEXT_TOKEN_BUDGET = int(os.getenv("PDF_TEXT_TOKEN_BUDGET", "80000"))

# ── Retry ─────────────────────────────────────────────────────────────────────

RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "2.0"))

# ── Prompt versioning ─────────────────────────────────────────────────────────

PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1.0")
