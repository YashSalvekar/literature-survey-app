import streamlit as st
import pandas as pd
import os

from steps.step1_search import run_literature_search
from steps.step3_pdf_download import download_pdfs
from steps.step4_pdf_summarizer import summarize_pdfs

st.set_page_config(page_title="Literature Survey Automation", layout="wide")

st.title("📚 Literature Survey Automation Platform")

BASE_DIR = os.getcwd()
DATA_DIR = os.path.join(BASE_DIR, "data")
PDF_DIR = os.path.join(DATA_DIR, "downloaded_pdfs")
SUMMARY_DIR = os.path.join("outputs", "summaries")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(SUMMARY_DIR, exist_ok=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "1️⃣ Literature Search",
    "2️⃣ Abstract Screening",
    "3️⃣ PDF Download",
    "4️⃣ PDF → 1-Pager Summary"
])

# ======================================================
# STEP 1 — SEARCH
# ======================================================
with tab1:
    st.header("Step 1 — Literature Search")

    query = st.text_input("Enter keyword / query")
    max_results = st.number_input("Max papers", 50, 1000, 300)

    if st.button("Run Literature Search"):
        with st.spinner("Searching literature..."):
            df = run_literature_search(query, max_results)
            df.to_csv(os.path.join(DATA_DIR, "search_results.csv"), index=False)
            st.session_state["search_df"] = df
            st.success(f"Found {len(df)} papers")

    if "search_df" in st.session_state:
        st.dataframe(st.session_state["search_df"], use_container_width=True)

# ======================================================
# STEP 2 — SCREENING
# ======================================================
with tab2:
    st.header("Step 2 — Abstract Screening (Manual Filtering)")

    path = os.path.join(DATA_DIR, "search_results.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        st.info("Edit / filter rows below, then click Save")

        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

        if st.button("Save Filtered Results"):
            edited_df.to_csv(os.path.join(DATA_DIR, "screened_results.csv"), index=False)
            st.session_state["screened_df"] = edited_df
            st.success("Filtered dataset saved")

    else:
        st.warning("Run Step 1 first")

# ======================================================
# STEP 3 — PDF DOWNLOAD
# ======================================================
with tab3:
    st.header("Step 3 — PDF Download")

    screened_path = os.path.join(DATA_DIR, "screened_results.csv")
    if os.path.exists(screened_path):
        df = pd.read_csv(screened_path)
        st.dataframe(df, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            only_reviews = st.checkbox("Only Reviews")
        with col2:
            top_n = st.number_input("Top N by citations (0 = All)", 0, 500, 0)
            top_n = None if top_n == 0 else top_n

        if st.button("Download PDFs"):
            with st.spinner("Downloading PDFs..."):
                files, updated_df = download_pdfs(
                    df,
                    output_dir=PDF_DIR,
                    only_reviews=only_reviews,
                    top_n=top_n
                )
                updated_df.to_csv(screened_path, index=False)
                st.success(f"Downloaded {len(files)} PDFs")

        if os.path.exists(PDF_DIR):
            pdfs = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
            st.write(f"PDFs downloaded: {len(pdfs)}")
            st.write(pdfs)

    else:
        st.warning("Complete Step 2 first")

# ======================================================
# STEP 4 — PDF SUMMARIZATION
# ======================================================
with tab4:
    st.header("Step 4 — PDF → 1-Pager Summarization")

    uploaded_files = st.file_uploader(
        "Upload PDFs (optional — or use downloaded PDFs)",
        type=["pdf"],
        accept_multiple_files=True
    )

    if uploaded_files:
        upload_dir = os.path.join(PDF_DIR, "uploaded")
        os.makedirs(upload_dir, exist_ok=True)

        for f in uploaded_files:
            with open(os.path.join(upload_dir, f.name), "wb") as out:
                out.write(f.read())

        pdf_dir = upload_dir
    else:
        pdf_dir = PDF_DIR

    if st.button("Generate 1-Pager Summaries"):
        with st.spinner("Summarizing PDFs..."):
            outputs = summarize_pdfs(pdf_dir, output_dir=SUMMARY_DIR)
            st.success("Summaries generated")

            for file, summary in outputs.items():
                st.subheader(file)
                st.text_area("Summary", summary, height=300)

        st.info("Word documents are saved in outputs/summaries/")
