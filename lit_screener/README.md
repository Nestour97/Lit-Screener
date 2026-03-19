# LLM Literature Screener

**Missing Data Handling Practices Study — LLM-Assisted Literature Screening & Variable Extraction**

Version 1.0 | Based on RA Task PDF (January 26, 2026)

---

## What this does

A local Python application that:
1. **Classifies** every paper in a batch (~50 PDFs) using an LLM
2. **Extracts** 50+ structured variables from eligible empirical quantitative papers
3. **Logs** all ambiguities, flags, and coding rationales
4. **Outputs** a fully formatted Excel workbook + Markdown summary report

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your API key
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (or ANTHROPIC_API_KEY)
```

### 3a. Run the Streamlit UI
```bash
streamlit run app.py
```

### 3b. Run from the command line (batch mode)
```bash
# Process all PDFs in a folder
python cli.py --pdf-dir data/pdfs

# Classification only (faster, cheaper)
python cli.py --pdf-dir data/pdfs --classify-only

# Load from a CSV of Google Drive links
python cli.py --csv paper_links.csv

# Reprocess specific papers
python cli.py --pdf-dir data/pdfs --rerun 003 007
```

---

## Where to put things

| Item | Location |
|------|----------|
| Local PDFs | `data/pdfs/` (name them `001.pdf`, `002.pdf`, etc.) |
| CSV of Drive links | Upload via UI, or pass with `--csv` |
| API keys | `.env` file (copy from `.env.example`) |
| Outputs | `outputs/` (auto-created) |

### CSV format for Google Drive links
```csv
paper_id,url
001,https://drive.google.com/file/d/FILEID/view
002,https://drive.google.com/open?id=FILEID
```

**Note:** Only publicly accessible Drive files can be auto-downloaded. For private files, download manually to `data/pdfs/{paper_id}.pdf`.

---

## Outputs

```
outputs/
  extraction_output.xlsx          ← Main workbook (5 sheets)
  extraction_log.jsonl            ← Machine-readable log
  cli_run.log                     ← Full run log (CLI mode)
  raw_model_outputs/
    {paper_id}_classification.json
    {paper_id}_extraction.json
  reports/
    summary_report.md
    classification_framework.md
normalized_text/
    {paper_id}.txt                ← Cached parsed text
```

### Excel workbook sheets

| Sheet | Contents |
|-------|----------|
| **Input** | One row per paper — filename, status, eligibility |
| **Classification** | One row per paper — category, confidence, review flag |
| **Extraction** | One row per study — all 50+ variables |
| **Log** | All issues, flags, and coding rationales |
| **Summary** | Descriptive statistics + full narrative report |

---

## Project structure

```
lit_screener/
  app.py                    ← Streamlit UI
  cli.py                    ← CLI batch runner
  requirements.txt
  README.md
  .env.example
  src/
    config.py               ← All configuration (env-vars)
    pipeline.py             ← Main orchestrator
    models/
      schemas.py            ← Pydantic data models
      enums.py              ← All coded field enumerations
    services/
      pdf_parser.py         ← PyMuPDF + pdfplumber, page-aware, cached
      llm_client.py         ← OpenAI/Anthropic abstraction
      classifier.py         ← Classification LLM call
      extractor.py          ← Variable extraction LLM call
      summarizer.py         ← Stats + report generation
      drive_loader.py       ← Google Drive download helper
      excel_writer.py       ← 5-sheet Excel output
      logger.py             ← JSONL + Python logging
    prompts/
      classification_prompt.txt   ← Prompt v1.0 for classification
      extraction_prompt.txt       ← Prompt v1.0 for extraction
      summary_prompt.txt          ← Prompt v1.0 for summary
    utils/
      retry_utils.py        ← Exponential-backoff decorator
      file_utils.py         ← JSON read/write helpers
      text_utils.py         ← Text cleaning, truncation, NA/NR
  data/
    pdfs/                   ← Put PDFs here
  outputs/                  ← All generated outputs
  tests/
    test_schemas.py
    test_pdf_parser.py
    test_excel_writer.py
    test_drive_loader.py
```

---

## Running tests

```bash
pytest tests/ -v
```

Tests cover: schema validation, PDF text parsing/caching, Excel output structure, Drive URL parsing.

---

## Schema assumptions & conservative defaults

The schema is derived directly from the RA Task PDF (Section 2.3.1, B1 Variable List). Where the task PDF was ambiguous, these conservative defaults were applied:

| Field | Assumption |
|-------|-----------|
| `confidence` | Stored as float 0–1 (not 3-level enum) for finer granularity; maps to High/Medium/Low for display |
| `mediator_name` when `mediator_present=0` | Written as "NA" (not applicable) |
| `moderator_name` when `moderator_present=0` | Written as "NA" |
| `missing_rate_value` when `missing_rate_reported=0` | Written as "NA" |
| `endogeneity_method` when `endogeneity_addressed=0` | Written as "NA" |
| Null values in general | Text fields → "NR" (not reported); inapplicable fields → "NA" |
| Multi-study papers | Separate extraction row per study; IDs suffixed "-S1", "-S2", etc. |
| Controls count | Excludes IVs and fixed effects — only explicitly labelled controls |
| Page number evidence | Left blank (rather than fabricated) if LLM cannot identify reliably; `needs_review=true` set |
| Journal field | Free-text abbreviation; no hard enumeration enforced (task lists examples not exhaustive list) |
| Prompt version | Tracked in all raw JSON outputs via `PROMPT_VERSION` env var |

---

## Adding a paper later / Rerunning one paper

```bash
# Place the new PDF in data/pdfs/042.pdf, then:
python cli.py --pdf-dir data/pdfs --rerun 042
```

The workbook will be regenerated including all previously processed papers.

---

## Switching to Anthropic

In `.env`:
```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-4-6
```

Or in the Streamlit sidebar, switch the provider dropdown.

---

## What still needs manual review

1. **Flagged papers** — Check the "Review Queue" tab in the UI or the Log sheet. These need a human decision before finalising the dataset.
2. **Page numbers** — The LLM may leave `dv_measurement_page` / `missing_handling_page` blank if evidence was unclear. Verify manually using the raw PDF.
3. **Multi-study papers** — Complex designs (e.g. 3+ studies with different DVs) may have imperfect study-splitting. Verify the Extraction sheet rows.
4. **Ambiguous variable roles** — Mediator/moderator distinctions sometimes require domain judgment; check flagged entries.
5. **Prompt tuning** — The default prompts (v1.0) are conservative starting points. After reviewing initial extractions, update `src/prompts/extraction_prompt.txt` and bump `PROMPT_VERSION`.
