import streamlit as st
import pandas as pd

from steps.step1_literature_search import run_literature_search
from steps.step2_filter_ui import step2_filter_ui
from steps.step3_pdf_downloader import download_pdfs
from steps.step4_pdf_summarizer import summarize_pdfs
from utils.file_utils import create_zip

st.set_page_config(page_title="Literature Survey Automation", layout="wide")
st.title("📚 Literature Survey Automation")

# =====================================================
# STEP 1 — SEARCH
# =====================================================
st.header("Step 1 — Literature Search")

query = st.text_input("Enter search query")
min_year = st.number_input("Minimum publication year", value=2016, step=1)
max_year = st.number_input("Maximum publication year", value=2026, step=1)

if st.button("🔍 Run Search"):
    with st.spinner("Searching literature sources..."):
        df = run_literature_search(query, min_year=min_year, max_year=max_year)
        st.session_state["step1_df"] = df

if "step1_df" in st.session_state:
    st.success(f"{len(st.session_state['step1_df'])} papers retrieved.")
    st.dataframe(st.session_state["step1_df"], use_container_width=True)

    st.download_button(
        "⬇ Download Step 1 Results (Excel)",
        data=st.session_state["step1_df"].to_excel(index=False),
        file_name="step1_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.divider()

# =====================================================
# STEP 2 — FILTER & SELECT
# =====================================================
st.header("Step 2 — Filter & Select Papers")

if "step1_df" not in st.session_state:
    st.warning("Run Step 1 first.")
else:
    selected_df = step2_filter_ui(st.session_state["step1_df"])

    if "step2_df" in st.session_state:
        st.success(f"{len(st.session_state['step2_df'])} papers selected.")
        st.dataframe(st.session_state["step2_df"], use_container_width=True)

st.divider()

# =====================================================
# STEP 3 — PDF DOWNLOAD
# =====================================================
st.header("Step 3 — Download PDFs")

source_option = st.radio("Source of paper list", ["From Step 2", "Upload Excel"], horizontal=True)

if source_option == "Upload Excel":
    uploaded_file = st.file_uploader("Upload filtered Excel", type=["xlsx"])
    if uploaded_file:
        st.session_state["step2_df"] = pd.read_excel(uploaded_file)

if "step2_df" not in st.session_state:
    st.warning("No filtered dataset available.")
else:
    st.dataframe(st.session_state["step2_df"], use_container_width=True)

    if st.button("📥 Download PDFs"):
        with st.spinner("Downloading PDFs..."):
            pdfs = download_pdfs(st.session_state["step2_df"])
            st.session_state["downloaded_pdfs"] = pdfs

    if "downloaded_pdfs" in st.session_state and st.session_state["downloaded_pdfs"]:
        st.success(f"{len(st.session_state['downloaded_pdfs'])} PDFs downloaded.")

        zip_buffer = create_zip(st.session_state["downloaded_pdfs"])
        st.download_button(
            "⬇ Download All PDFs (ZIP)",
            data=zip_buffer,
            file_name="downloaded_pdfs.zip",
            mime="application/zip",
        )

st.divider()

# =====================================================
# STEP 4 — PDF → 1-PAGER SUMMARIZATION
# =====================================================
st.header("Step 4 — Generate 1-Pager Summaries")

pdf_source = st.radio(
    "Select PDF Source",
    ["From Step 3 Downloads", "Upload PDFs"],
    horizontal=True,
)

pdf_files = None

if pdf_source == "From Step 3 Downloads":
    pdf_files = st.session_state.get("downloaded_pdfs")
else:
    uploaded_pdfs = st.file_uploader(
        "Upload one or more PDFs",
        type=["pdf"],
        accept_multiple_files=True,
    )
    if uploaded_pdfs:
        pdf_files = {f.name: f.read() for f in uploaded_pdfs}

if not pdf_files:
    st.warning("No PDFs available.")
else:
    st.success(f"{len(pdf_files)} PDFs ready for summarization.")

    if st.button("🧠 Generate Summaries"):
        with st.spinner("Generating summaries..."):
            summaries = summarize_pdfs(pdf_files)
            st.session_state["summaries"] = summaries

    if "summaries" in st.session_state:
        for fname, text in st.session_state["summaries"].items():
            st.subheader(fname)
            st.text_area("Summary", text, height=280)

        zip_buffer = create_zip({k: v.encode("utf-8") for k, v in st.session_state["summaries"].items()})
        st.download_button(
            "⬇ Download All Summaries (ZIP)",
            data=zip_buffer,
            file_name="paper_summaries.zip",
            mime="application/zip",
        )
