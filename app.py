import streamlit as st
import pandas as pd
import os
import shutil
import tempfile

from steps.step1_literature_search import run_search
from steps.step2_filter import filter_dataframe
from steps.step3_pdf_download import run_pdf_download
from steps.step4_pdf_summarizer import run_pdf_summarization
from utils.io_helpers import ensure_dir, zip_folder

st.set_page_config(page_title="Literature Survey Automation", layout="wide")

# =========================================================
# OUTPUT DIRS
# =========================================================
BASE_OUTPUT_DIR = "outputs"
SEARCH_DIR = ensure_dir(os.path.join(BASE_OUTPUT_DIR, "search_results"))
FILTER_DIR = ensure_dir(os.path.join(BASE_OUTPUT_DIR, "filtered_results"))
PDF_DIR = ensure_dir(os.path.join(BASE_OUTPUT_DIR, "pdfs"))
SUMMARY_DIR = ensure_dir(os.path.join(BASE_OUTPUT_DIR, "summaries"))
ZIP_DIR = ensure_dir(os.path.join(BASE_OUTPUT_DIR, "zips"))

st.title("📚 Literature Survey Automation Platform")

# =========================================================
# SESSION STATE
# =========================================================
if "step1_df" not in st.session_state:
    st.session_state.step1_df = None
if "step2_df" not in st.session_state:
    st.session_state.step2_df = None
if "step3_df" not in st.session_state:
    st.session_state.step3_df = None

# =========================================================
# STEP 1 — SEARCH
# =========================================================
st.header("Step 1 — Literature Search")

with st.form("step1_form"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        keyword = st.text_input("Keyword", value="isobutene")
    with col2:
        min_year = st.number_input("From Year", min_value=1900, max_value=2100, value=2016)
    with col3:
        max_year = st.number_input("To Year", min_value=1900, max_value=2100, value=2026)
    with col4:
        max_results = st.number_input("Max results (0 = all)", min_value=0, value=0)

    run_step1 = st.form_submit_button("🔍 Run Search")

if run_step1:
    with st.spinner("Running literature search..."):
        df = run_search(keyword, min_year, max_year, max_results=max_results if max_results > 0 else None)

    st.session_state.step1_df = df
    path = os.path.join(SEARCH_DIR, f"{keyword}_raw_results.xlsx")
    df.to_excel(path, index=False)
    st.success(f"✅ {len(df)} papers found")
    st.download_button("⬇ Download Raw Results Excel", data=open(path, "rb"), file_name=os.path.basename(path))

if st.session_state.step1_df is not None:
    st.dataframe(st.session_state.step1_df, use_container_width=True)

# =========================================================
# STEP 2 — FILTER, SELECT ROWS, OR UPLOAD
# =========================================================
st.header("Step 2 — Filter / Select Rows or Upload Filtered Excel")

uploaded_file = st.file_uploader("📤 Upload filtered Excel (optional)", type=["xlsx"])

if uploaded_file:
    df_uploaded = pd.read_excel(uploaded_file)
    st.session_state.step2_df = df_uploaded
    path = os.path.join(FILTER_DIR, "uploaded_filtered_results.xlsx")
    df_uploaded.to_excel(path, index=False)
    st.success(f"✅ Uploaded {len(df_uploaded)} rows from Excel")

elif st.session_state.step1_df is not None:
    df = st.session_state.step1_df

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        min_citations = st.number_input("Min citations", min_value=0, value=0)
    with col2:
        reviews_only = st.checkbox("Reviews only")
    with col3:
        open_access_only = st.checkbox("Open access only")
    with col4:
        top_n = st.number_input("Top N (0 = all)", min_value=0, value=0)

    year_min, year_max = int(df["Publication Year"].min()), int(df["Publication Year"].max())
    year_range = st.slider("Year range", year_min, year_max, (year_min, year_max))

    if st.button("🎯 Apply Filters"):
        filtered_df = filter_dataframe(
            df,
            min_citations=min_citations,
            reviews_only=reviews_only,
            open_access_only=open_access_only,
            year_range=year_range,
            top_n=top_n if top_n > 0 else None
        )
        st.session_state.step2_df = filtered_df
        path = os.path.join(FILTER_DIR, "filtered_results.xlsx")
        filtered_df.to_excel(path, index=False)
        st.success(f"✅ {len(filtered_df)} papers after filtering")
        st.download_button("⬇ Download Filtered Excel", data=open(path, "rb"), file_name="filtered_results.xlsx")

    # ---------- NEW: Row Selection ----------
    st.subheader("✅ Or Select Specific Rows Manually")
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        key="step2_editor"
    )

    if st.button("📌 Use Selected Rows"):
        st.session_state.step2_df = edited_df
        path = os.path.join(FILTER_DIR, "ui_selected_results.xlsx")
        edited_df.to_excel(path, index=False)
        st.success(f"✅ {len(edited_df)} rows selected manually")
        st.download_button("⬇ Download Selected Excel", data=open(path, "rb"), file_name="ui_selected_results.xlsx")

if st.session_state.step2_df is not None:
    st.dataframe(st.session_state.step2_df, use_container_width=True)

# =========================================================
# STEP 3 — PDF DOWNLOAD (FROM STEP 2)
# =========================================================
st.header("Step 3 — PDF Download")

if st.session_state.step2_df is not None:
    col1, col2 = st.columns(2)
    with col1:
        delay = st.number_input("Request delay (seconds)", min_value=0.0, value=2.0, step=0.5)
    with col2:
        run_step3 = st.button("📥 Download PDFs")

    if run_step3:
        with st.spinner("Downloading PDFs..."):
            step3_df = run_pdf_download(st.session_state.step2_df, output_dir=PDF_DIR, delay=delay)

        st.session_state.step3_df = step3_df
        step3_path = os.path.join(PDF_DIR, "pdf_download_results.xlsx")
        step3_df.to_excel(step3_path, index=False)

        st.success("✅ PDF download completed")
        st.download_button("⬇ Download PDF Status Excel", data=open(step3_path, "rb"), file_name="pdf_download_results.xlsx")

        zip_path = os.path.join(ZIP_DIR, "downloaded_pdfs.zip")
        zip_folder(PDF_DIR, zip_path)
        st.download_button("📦 Download All PDFs (ZIP)", data=open(zip_path, "rb"), file_name="downloaded_pdfs.zip")

if st.session_state.step3_df is not None:
    st.dataframe(st.session_state.step3_df, use_container_width=True)

# =========================================================
# STEP 4 — PDF → ONE-PAGER SUMMARIES
# =========================================================
st.header("Step 4 — PDF → 1-Pager Summaries")

st.subheader("📤 Option A — Upload PDFs from Local")
uploaded_pdfs = st.file_uploader(
    "Upload one or more PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_pdfs:
    for pdf in uploaded_pdfs:
        with open(os.path.join(PDF_DIR, pdf.name), "wb") as f:
            f.write(pdf.read())
    st.success(f"✅ Uploaded {len(uploaded_pdfs)} PDFs to processing folder")

st.subheader("📁 Option B — Use PDFs Downloaded in Step 3")

if os.listdir(PDF_DIR):
    if st.button("🧠 Generate 1-Pager Summaries"):
        with st.spinner("Generating summaries..."):
            results = run_pdf_summarization(PDF_DIR, output_dir=SUMMARY_DIR)

        summary_paths = [r["summary_path"] for r in results]

        st.success(f"✅ Generated {len(summary_paths)} summaries")

        for path in summary_paths:
            with open(path, "rb") as f:
                st.download_button(
                    label=f"⬇ {os.path.basename(path)}",
                    data=f,
                    file_name=os.path.basename(path),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

        zip_path = os.path.join(ZIP_DIR, "one_pager_summaries.zip")
        zip_folder(SUMMARY_DIR, zip_path)
        st.download_button("📦 Download All Summaries (ZIP)", data=open(zip_path, "rb"), file_name="one_pager_summaries.zip")

else:
    st.info("ℹ No PDFs found yet. Run Step 3 or upload PDFs above.")
