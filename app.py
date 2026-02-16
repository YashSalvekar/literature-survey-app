import streamlit as st
import pandas as pd
import os
import io
from steps.step1_literature_search import run_literature_search
from steps.step2_filter_ui import step2_filter_ui
from steps.step3_pdf_downloader import download_pdfs
from steps.step4_pdf_summarizer import summarize_pdfs
from utils.file_utils import create_zip
from utils.io_helpers import ensure_dir
import io
import zipfile
from spellchecker import SpellChecker
from datetime import datetime


st.set_page_config(page_title="Literature Survey Automation", layout="wide")
st.title("📚 Literature Survey Automation Platform")

# =====================================================
# OUTPUT DIRECTORIES
# =====================================================
BASE_OUTPUT_DIR = "outputs"
SEARCH_DIR = ensure_dir(os.path.join(BASE_OUTPUT_DIR, "search_results"))
FILTER_DIR = ensure_dir(os.path.join(BASE_OUTPUT_DIR, "filtered_results"))
PDF_DIR = ensure_dir(os.path.join(BASE_OUTPUT_DIR, "pdfs"))
SUMMARY_DIR = ensure_dir(os.path.join(BASE_OUTPUT_DIR, "summaries"))

# =====================================================
# STEP 1 — SEARCH
# =====================================================
st.header("Step 1 — Literature Search")

# 🎯 Inputs
query = st.text_input("Enter search query")


# 🔤 Spell Check Suggestion
# =====================================================

spell = SpellChecker()

corrected_query = None

if query.strip():
    words = query.split()
    misspelled = spell.unknown(words)

    if misspelled:
        corrected_words = [
            spell.correction(word) if word in misspelled else word
            for word in words
        ]
        corrected_query = " ".join(corrected_words)

        if corrected_query != query:
            st.warning(f"Did you mean: **{corrected_query}** ?")

            if st.button("Apply Correction"):
                query = corrected_query


current_year = datetime.now().year
year_options = list(range(current_year, 1990, -1))

col1, col2 = st.columns(2)

with col1:
    min_year = st.selectbox(
        "Minimum publication year",
        options=year_options,
        index=year_options.index(2016) if 2016 in year_options else 0
    )

with col2:
    max_year = st.selectbox(
        "Maximum publication year",
        options=year_options,
        index=0
    )

# =====================================================
# ✅ LIVE VALIDATION
# =====================================================

error_message = None

if not query.strip():
    error_message = "Search query is required."

elif min_year > max_year:
    error_message = "Minimum publication year cannot be greater than maximum publication year."

# Show inline error under inputs
if error_message:
    st.error(error_message)

# =====================================================
# 🔍 Run Search (Disabled if invalid)
# =====================================================

search_disabled = error_message is not None

if st.button("🔍 Run Search", disabled=search_disabled):

    with st.spinner("Searching literature sources..."):
        df = run_literature_search(query, min_year=min_year, max_year=max_year)

        # 🔧 SAFETY: handle (df, status)
        if isinstance(df, tuple):
            df = df[0]

        st.session_state["step1_df"] = df

        path = os.path.join(SEARCH_DIR, "step1_raw_results.xlsx")
        df.to_excel(path, index=False)

if "step1_df" in st.session_state:
    st.success(f"{len(st.session_state['step1_df'])} papers retrieved.")
    st.dataframe(st.session_state["step1_df"], use_container_width=True)

    # 🔧 FIX: Step 1 download must use step1_df, not step2_df
    buffer = io.BytesIO()
    st.session_state["step1_df"].to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        "⬇ Download Step 1 Results (Excel)",
        data=buffer,
        file_name="step1_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.divider()

# =====================================================
# STEP 2 — FILTER, SELECT, OR UPLOAD
# =====================================================
st.header("Step 2 — Filter & Select Papers")

source_option = st.radio(
    "Source of paper list",
    ["From Step 1", "Upload filtered Excel"],
    horizontal=True,
)

candidate_df = None

if source_option == "Upload filtered Excel":
    uploaded_file = st.file_uploader("Upload filtered Excel", type=["xlsx"])
    if uploaded_file:
        candidate_df = pd.read_excel(uploaded_file)
        st.info("Uploaded file loaded. Review and confirm below.")

if source_option == "From Step 1":
    if "step1_df" not in st.session_state:
        st.warning("Run Step 1 first.")
    else:
        candidate_df = step2_filter_ui(st.session_state["step1_df"])

# ---------- PREVIEW + COMMIT ----------
if candidate_df is not None:
    st.subheader("Final Papers Going to Step 3")
    st.dataframe(candidate_df, use_container_width=True)
    st.success(f"{len(candidate_df)} papers selected.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Use Selected Papers → Step 3"):
            st.session_state["step2_df"] = candidate_df
            path = os.path.join(FILTER_DIR, "step2_filtered_results.xlsx")
            candidate_df.to_excel(path, index=False)
            st.success("Filtered papers saved and forwarded to Step 3.")

    with col2:
        buffer = io.BytesIO()
        candidate_df.to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button(
            "⬇ Download Step 2 Results (Excel)",
            data=buffer,
            file_name="step2_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )





# =====================================================
# STEP 3 — PDF DOWNLOAD
# =====================================================
st.header("Step 3 — Download PDFs")

if "step2_df" not in st.session_state:
    st.warning("No filtered dataset available.")
else:
    st.dataframe(st.session_state["step2_df"], use_container_width=True)

    if st.button("📥 Download PDFs"):
        with st.spinner("Downloading PDFs..."):
            pdf_paths, report_df = download_pdfs(
                st.session_state["step2_df"],
                output_dir=PDF_DIR,
                report_path="outputs/pdf_download_report.xlsx"
                
            )
            st.session_state["downloaded_pdfs"] = pdf_paths
            st.session_state["download_report_df"] = report_df

    # -----------------------------
    # Always show download buttons
    # -----------------------------
    if "downloaded_pdfs" in st.session_state:

        st.success(f"{len(st.session_state['downloaded_pdfs'])} PDFs downloaded.")

        # ZIP: PDFs + Excel report
        files_for_zip = {
            os.path.basename(p): open(p, "rb").read()
            for p in st.session_state["downloaded_pdfs"]
        }

        if "download_report_df" in st.session_state:
            excel_buffer = io.BytesIO()
            st.session_state["download_report_df"].to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)
            files_for_zip["pdf_download_report.xlsx"] = excel_buffer.read()

        zip_buffer = create_zip(files_for_zip)

        st.download_button(
            "⬇ Download PDFs + Report (ZIP)",
            data=zip_buffer,
            file_name="pdfs_and_report.zip",
            mime="application/zip",
            key="zip_download"
        )

        # Excel-only download
        if "download_report_df" in st.session_state:
            excel_buffer = io.BytesIO()
            st.session_state["download_report_df"].to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)

            st.download_button(
                "⬇ Download Download Report (Excel)",
                data=excel_buffer,
                file_name="pdf_download_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="excel_download"
            )



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
    if "downloaded_pdfs" in st.session_state:
        pdf_files = {
            os.path.basename(p): open(p, "rb").read()
            for p in st.session_state["downloaded_pdfs"]
        }
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
            summaries = summarize_pdfs(pdf_files, output_dir=SUMMARY_DIR)
            st.session_state["summaries"] = summaries

    if "summaries" in st.session_state:
    
        st.markdown("### 📄 Generated Summaries")
    
        for fname, file_bytes in st.session_state["summaries"].items():
            st.subheader(fname)
    
            st.download_button(
                label=f"⬇ Download {fname}",
                data=file_bytes,
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        # ZIP ALL DOCX FILES
        #zip_buffer = create_zip(st.session_state["summaries"])
        
        def create_zip_from_dict(files_dict):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for fname, fbytes in files_dict.items():
                    zipf.writestr(fname, fbytes)
            buffer.seek(0)
            return buffer
        
        zip_buffer = create_zip_from_dict(st.session_state["summaries"])

    
        st.download_button(
            "⬇ Download All Summaries (ZIP)",
            data=zip_buffer,
            file_name="paper_summaries.zip",
            mime="application/zip",
        )

   





