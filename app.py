import streamlit as st
import pandas as pd
import io

from steps.step1_literature_search import run_literature_search
from steps.step2_filter_ui import step2_filter_ui
from steps.step3_pdf_downloader import download_pdfs
from steps.step4_pdf_summarizer import summarize_pdfs

st.set_page_config(page_title="Literature Survey Automation", layout="wide")
st.title("📚 Literature Survey Automation")

# =====================================================
# SESSION STATE INIT
# =====================================================
for k in ["step1_df", "step2_df", "step3_df", "step4_df"]:
    if k not in st.session_state:
        st.session_state[k] = None

# =====================================================
# STEP 1 — LITERATURE SEARCH
# =====================================================
st.header("✅ Step 1 — Literature Search")

keyword = st.text_input("Enter keyword(s)", value="isobutene")
min_year = st.number_input("Minimum year", value=2016, step=1)
max_results = st.number_input("Max results (0 = all possible)", value=500, step=50)

if st.button("🔍 Run Literature Search"):
    with st.spinner("Searching Semantic Scholar, OpenAlex, arXiv..."):
        df = run_literature_search(
            keyword=keyword,
            min_year=min_year,
            max_results=None if max_results == 0 else int(max_results),
        )
        st.session_state["step1_df"] = df
        st.success(f"✅ Step 1 completed — {len(df)} papers found")

if st.session_state["step1_df"] is not None:
    st.dataframe(st.session_state["step1_df"], use_container_width=True)

    buffer = io.BytesIO()
    st.session_state["step1_df"].to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        "⬇ Download Step 1 Results (Excel)",
        data=buffer,
        file_name="step1_literature_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# =====================================================
# STEP 2 — FILTER / SELECTION
# =====================================================
st.header("✅ Step 2 — Filter / Select Papers")

if st.session_state["step1_df"] is None:
    st.info("Run Step 1 first.")
else:
    st.session_state["step2_df"] = step2_filter_ui(st.session_state["step1_df"])

    if st.session_state["step2_df"] is not None and not st.session_state["step2_df"].empty:
        st.success(f"✅ Step 2 completed — {len(st.session_state['step2_df'])} papers selected")

        buffer = io.BytesIO()
        st.session_state["step2_df"].to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            "⬇ Download Step 2 Results (Excel)",
            data=buffer,
            file_name="step2_filtered_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# =====================================================
# STEP 3 — PDF DOWNLOAD
# =====================================================
st.header("✅ Step 3 — Download PDFs")

if st.session_state["step2_df"] is None:
    st.info("Complete Step 2 first.")
elif st.button("⬇ Download PDFs"):
    with st.spinner("Downloading PDFs..."):
        df = download_pdfs(st.session_state["step2_df"])
        st.session_state["step3_df"] = df
        st.success("✅ Step 3 completed")

if st.session_state["step3_df"] is not None:
    st.dataframe(st.session_state["step3_df"], use_container_width=True)

# =====================================================
# STEP 4 — PDF SUMMARIZATION
# =====================================================
st.header("✅ Step 4 — Summarize PDFs")

if st.session_state["step3_df"] is None:
    st.info("Complete Step 3 first.")
elif st.button("🧠 Run Summarization"):
    with st.spinner("Summarizing PDFs..."):
        df = summarize_pdfs(st.session_state["step3_df"])
        st.session_state["step4_df"] = df
        st.success("✅ Step 4 completed")

if st.session_state["step4_df"] is not None:
    st.dataframe(st.session_state["step4_df"], use_container_width=True)

    buffer = io.BytesIO()
    st.session_state["step4_df"].to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        "⬇ Download Final Results (Excel)",
        data=buffer,
        file_name="final_summarized_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
