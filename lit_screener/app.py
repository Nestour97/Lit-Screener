"""
Streamlit UI — works locally AND on Streamlit Cloud.

Local: reads from .env file
Streamlit Cloud: reads from st.secrets (Settings → Secrets in the Cloud dashboard)
"""

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd

# ── Load secrets: Streamlit Cloud first, then .env ────────────────────────────
def _load_secrets():
    """Populate os.environ from st.secrets (Cloud) or .env (local)."""
    keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_PROVIDER",
            "OPENAI_MODEL", "ANTHROPIC_MODEL"]
    # Streamlit Cloud secrets take priority
    for k in keys:
        try:
            v = st.secrets.get(k, "")
            if v:
                os.environ[k] = v
        except Exception:
            pass
    # Fall back to .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

_load_secrets()

from src.config import DATA_DIR, OUTPUTS_DIR, REPORTS_DIR
from src.services.llm_client import LLMClient
from src.services.drive_loader import load_papers_from_csv
from src.pipeline import run_pipeline

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

st.set_page_config(
    page_title="LLM Literature Screener",
    page_icon="📄",
    layout="wide",
)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {"pipeline_results": None, "running": False,
             "log_lines": [], "progress": 0.0}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")

    st.subheader("LLM Provider")
    provider = st.selectbox("Provider", ["groq", "openai", "anthropic"], index=0)

    if provider == "groq":
        api_key = st.text_input(
            "Groq API Key", type="password",
            value=os.getenv("GROQ_API_KEY", ""),
            help="Get a free key at console.groq.com",
        )
        model = st.selectbox("Model", [
            "llama-3.3-70b-versatile", "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it",
        ], help="llama-3.3-70b-versatile = best quality")
        # Set immediately so pipeline picks up the live value
        os.environ["GROQ_API_KEY"] = api_key
        os.environ["GROQ_MODEL"] = model

    elif provider == "anthropic":
        api_key = st.text_input(
            "Anthropic API Key", type="password",
            value=os.getenv("ANTHROPIC_API_KEY", ""),
            help="Get one at console.anthropic.com — starts with sk-ant-...",
        )
        model = st.selectbox("Model", [
            "claude-opus-4-6", "claude-sonnet-4-6",
        ], help="Opus 4.6 = best for extraction. Sonnet 4.6 = faster.")
        os.environ["ANTHROPIC_API_KEY"] = api_key
        os.environ["ANTHROPIC_MODEL"] = model

    else:  # openai
        api_key = st.text_input(
            "OpenAI API Key", type="password",
            value=os.getenv("OPENAI_API_KEY", ""),
            help="Get one at platform.openai.com — starts with sk-...",
        )
        model = st.selectbox("Model", ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"])
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_MODEL"] = model

    os.environ["LLM_PROVIDER"] = provider

    # Live key status indicator
    if api_key and len(api_key) > 10:
        st.success("✅ API key set")
    elif api_key:
        st.warning("⚠️ Key looks too short — double-check it")
    else:
        st.error("⛔ No API key — paste it above")

    if st.button("🔌 Test connection", disabled=not api_key):
        with st.spinner("Testing…"):
            try:
                from src.services.llm_client import LLMClient
                test_client = LLMClient(provider=provider, model=model)
                resp = test_client.complete(
                    system="You are a helpful assistant.",
                    user="Reply with exactly: OK",
                    max_tokens=10,
                )
                st.success(f"✅ Connected! Model replied: {resp.strip()}")
            except Exception as e:
                st.error(f"❌ Connection failed: {e}")

    st.divider()
    st.subheader("Run Options")
    run_extraction = st.checkbox(
        "Run full variable extraction",
        value=True,
        help="Uncheck for classification only — much cheaper for a first pass.",
    )

    st.divider()
    with st.expander("💡 Tips"):
        st.markdown("""
**Recommended workflow:**
1. First run **classification only** (fast, cheap)
2. Review the Review Queue tab
3. Run **full extraction** on confirmed eligible papers

**Best Groq model for extraction:** `llama-3.3-70b-versatile`
**Fastest Groq model:** `llama-3.1-8b-instant`

Groq is **free** to start — get your key at console.groq.com
        """)


# ── Main tabs ─────────────────────────────────────────────────────────────────
st.title("📄 LLM Literature Screener")
st.caption("Missing Data Handling Practices Study — Variable Extraction Workflow")

tab_upload, tab_run, tab_results, tab_review, tab_detail = st.tabs([
    "📂 Upload", "▶️ Run", "📊 Results", "🔍 Review Queue", "🔬 Paper Detail",
])


# ── Tab 1: Upload ─────────────────────────────────────────────────────────────
with tab_upload:
    st.header("Upload Papers")
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Option A — Upload PDFs")
        uploaded_pdfs = st.file_uploader(
            "Upload PDF files", type="pdf", accept_multiple_files=True,
        )
        if uploaded_pdfs:
            save_dir = DATA_DIR / "pdfs"
            save_dir.mkdir(parents=True, exist_ok=True)
            for uf in uploaded_pdfs:
                dest = save_dir / uf.name
                dest.write_bytes(uf.getbuffer())
            st.success(f"✅ Saved {len(uploaded_pdfs)} PDF(s) to `data/pdfs/`")

    with col_b:
        st.subheader("Option B — CSV with Google Drive Links")
        st.caption("CSV columns: `paper_id`, `url`")
        sample_csv = "paper_id,url\n001,https://drive.google.com/file/d/FILEID/view"
        st.download_button("⬇️ Download sample CSV", sample_csv,
                           file_name="sample_links.csv", mime="text/csv")
        uploaded_csv = st.file_uploader("Upload CSV / XLSX", type=["csv", "xlsx"])
        if uploaded_csv:
            tmp_path = DATA_DIR / "paper_links.csv"
            tmp_path.write_bytes(uploaded_csv.getbuffer())
            with st.spinner("Downloading from Google Drive…"):
                try:
                    results = load_papers_from_csv(tmp_path, DATA_DIR / "pdfs")
                    ok = sum(1 for v in results.values() if v)
                    fail = len(results) - ok
                    st.success(f"✅ Downloaded {ok} paper(s).")
                    if fail:
                        st.warning(
                            f"⚠️ {fail} file(s) couldn't be downloaded "
                            "(private Drive files must be downloaded manually)."
                        )
                except Exception as e:
                    st.error(f"CSV error: {e}")

    st.divider()
    st.subheader("Papers ready to process")
    pdf_dir = DATA_DIR / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if pdfs:
        st.dataframe(
            pd.DataFrame({
                "Filename": [p.name for p in pdfs],
                "Size (KB)": [round(p.stat().st_size / 1024, 1) for p in pdfs],
            }),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No PDFs yet. Upload some above.")


# ── Tab 2: Run ────────────────────────────────────────────────────────────────
with tab_run:
    st.header("Run Pipeline")

    pdf_dir = DATA_DIR / "pdfs"
    pdfs = sorted(pdf_dir.glob("*.pdf"))

    if not pdfs:
        st.warning("No PDFs found. Go to the Upload tab first.")
    else:
        st.info(f"Found **{len(pdfs)}** PDF(s) ready to process.")

        selected_names = st.multiselect(
            "Select papers to process (default = all)",
            options=[p.name for p in pdfs],
            default=[p.name for p in pdfs],
        )
        selected_pdfs = [p for p in pdfs if p.name in selected_names]

        # Check the live env var, not just the local variable
        live_key = os.environ.get(f"{provider.upper()}_API_KEY", "")
        if not live_key:
            st.error("⛔ No API key set — paste it in the sidebar.")
        else:
            col1, col2 = st.columns([1, 3])
            run_btn = col1.button(
                "▶️ Run Pipeline",
                type="primary",
                disabled=st.session_state.running or not selected_pdfs,
            )

            if run_btn:
                st.session_state.running = True
                st.session_state.log_lines = []
                st.session_state.pipeline_results = None

                progress_bar = st.progress(0)
                status_text = st.empty()
                log_box = st.empty()

                def progress_cb(paper_id, message, progress):
                    st.session_state.log_lines.append(f"[{paper_id}] {message}")
                    progress_bar.progress(min(float(progress), 1.0))
                    status_text.text(f"[{paper_id}] {message}")
                    log_box.code("\n".join(st.session_state.log_lines[-15:]))

                try:
                    import importlib, src.config as cfg_mod
                    importlib.reload(cfg_mod)
                    client = LLMClient(provider=provider, model=model)
                    results = run_pipeline(
                        pdf_paths=selected_pdfs,
                        client=client,
                        run_extraction=run_extraction,
                        output_dir=OUTPUTS_DIR,
                        progress_cb=progress_cb,
                    )
                    st.session_state.pipeline_results = results
                    st.session_state.running = False
                    progress_bar.progress(1.0)
                    status_text.text("✅ Pipeline complete!")
                    n_cls = len(results["classifications"])
                    n_ext = len(results["extractions"])
                    if n_cls == 0:
                        st.error("⚠️ 0 papers classified — LLM call failed. Check errors below.")
                        errors = [e for e in results.get("log_entries", []) if e.level == "error"]
                        for e in errors:
                            st.error(f"**[{e.paper_id}]** {e.message}")
                    else:
                        st.success(f"Done! Classified {n_cls} paper(s), extracted {n_ext} study record(s).")
                except Exception as exc:
                    st.session_state.running = False
                    st.error(f"Pipeline error: {exc}")
                    raise

        # Download button (persists after run)
        if st.session_state.pipeline_results:
            wb = st.session_state.pipeline_results.get("workbook_path")
            if wb and Path(wb).exists():
                st.divider()
                with open(wb, "rb") as f:
                    st.download_button(
                        "⬇️ Download extraction_output.xlsx",
                        data=f.read(),
                        file_name="extraction_output.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                    )


# ── Tab 3: Results ────────────────────────────────────────────────────────────
with tab_results:
    st.header("Results Overview")
    results = st.session_state.pipeline_results

    if not results:
        st.info("Run the pipeline first.")
    else:
        stats = results.get("stats", {})
        cls_list = results.get("classifications", [])
        ext_list = results.get("extractions", [])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Papers", stats.get("total_papers", 0))
        c2.metric("Eligible", stats.get("eligible_count", 0))
        c3.metric("Studies Extracted", stats.get("extractions_count", 0))
        c4.metric("Needs Review", stats.get("needs_review_count", 0))

        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("Classification breakdown")
            by_cat = stats.get("by_category", {})
            if by_cat:
                st.bar_chart(pd.Series(by_cat))
        with col_r:
            st.subheader("Missing data handling methods")
            mh = stats.get("missing_handling_distribution", {})
            if mh:
                st.bar_chart(pd.Series(mh))

        st.subheader("Missing data reporting rates")
        c1, c2, c3 = st.columns(3)
        c1.metric("Mentioned %", f"{stats.get('missing_mentioned_pct', 0):.1f}%")
        c2.metric("Rate Reported %", f"{stats.get('missing_rate_reported_pct', 0):.1f}%")
        c3.metric("Justified %", f"{stats.get('missing_justified_pct', 0):.1f}%")

        st.divider()
        if cls_list:
            st.subheader("Classification table")
            df = pd.DataFrame([c.model_dump() for c in cls_list])
            st.dataframe(
                df[["paper_id", "title", "classification",
                    "eligible_for_full_extraction", "confidence", "needs_review"]],
                use_container_width=True, hide_index=True,
            )

        summary = results.get("summary_md", "")
        if summary:
            st.divider()
            st.subheader("Summary Report")
            st.markdown(summary)
            st.download_button("⬇️ Download report (.md)", summary,
                               file_name="summary_report.md", mime="text/markdown")


# ── Tab 4: Review Queue ───────────────────────────────────────────────────────
with tab_review:
    st.header("🔍 Review Queue — Flagged Papers")
    results = st.session_state.pipeline_results

    if not results:
        st.info("Run the pipeline first.")
    else:
        cls_list = results.get("classifications", [])
        ext_list = results.get("extractions", [])

        flagged_cls = [c for c in cls_list if c.needs_review]
        flagged_ext = [e for e in ext_list if e.needs_review]

        st.subheader(f"Flagged classifications ({len(flagged_cls)})")
        if flagged_cls:
            st.dataframe(
                pd.DataFrame([{
                    "Paper_ID": c.paper_id,
                    "Classification": c.classification,
                    "Confidence": c.confidence,
                    "Flag Reason": c.flag_reason,
                } for c in flagged_cls]),
                use_container_width=True, hide_index=True,
            )
        else:
            st.success("No flagged classifications ✅")

        st.subheader(f"Flagged extractions ({len(flagged_ext)})")
        if flagged_ext:
            st.dataframe(
                pd.DataFrame([{
                    "Study_ID": e.paper_id,
                    "Flag Reason": e.flag_reason,
                    "Confidence": e.confidence,
                    "Notes": e.coding_notes,
                } for e in flagged_ext]),
                use_container_width=True, hide_index=True,
            )
        else:
            st.success("No flagged extractions ✅")

        st.subheader("Full log")
        log_entries = results.get("log_entries", [])
        if log_entries:
            df_log = pd.DataFrame([e.model_dump() for e in log_entries])
            level_filter = st.multiselect(
                "Filter by level",
                ["info", "warning", "flag", "error"],
                default=["warning", "flag", "error"],
            )
            filtered = df_log[df_log["level"].isin(level_filter)]
            st.dataframe(filtered, use_container_width=True, hide_index=True)


# ── Tab 5: Paper Detail ───────────────────────────────────────────────────────
with tab_detail:
    st.header("🔬 Paper Detail View")
    results = st.session_state.pipeline_results

    if not results:
        st.info("Run the pipeline first.")
    else:
        cls_list = results.get("classifications", [])
        ext_list = results.get("extractions", [])

        paper_ids = [c.paper_id for c in cls_list]
        if paper_ids:
            selected_id = st.selectbox("Select paper", paper_ids)
            cls = next((c for c in cls_list if c.paper_id == selected_id), None)
            studies = [e for e in ext_list if e.base_paper_id == selected_id]

            if cls:
                with st.expander("Classification", expanded=True):
                    st.json(cls.model_dump())

            if studies:
                for study in studies:
                    with st.expander(f"Extraction — {study.paper_id}", expanded=True):
                        st.json(study.model_dump())

                from src.config import RAW_OUTPUTS_DIR
                raw_path = RAW_OUTPUTS_DIR / f"{selected_id}_extraction.json"
                if raw_path.exists():
                    with st.expander("Raw model output (JSON)"):
                        st.code(raw_path.read_text(), language="json")
            elif cls and not cls.eligible_for_full_extraction:
                st.info(f"Not eligible for extraction ({cls.classification}).")
