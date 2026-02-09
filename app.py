import streamlit as st
import pandas as pd

from steps.step1_literature_search import run_literature_search
from steps.step2_filter_ui import step2_filter_ui
from steps.step3_pdf_downloader import download_pdfs
from steps.step4_pdf_summarizer import summarize_pdfs
from utils.file_utils import create_zip

st.set_page_config(page_title="Literature Survey Automation", layout="wide")

st.title("📚 Literature Survey Automation Platform")

tabs = st.tabs(["Step 1 — Search", "Step 2 — Filter", "Step 3 — PDFs", "Step 4 — Summaries"])

# ---------------- STEP 1 ----------------
with tabs[0]:
    st.header("Step 1 — Literature Search")

    query = st.text_input("Enter search query")
    max_results = st.slider("Max results", 5, 100, 20)

    if st.button("Run Search"):
        df = run_literature_search(query, max_results)
        st.session_state["step1_df"] = df
        st.dataframe(df, use_container_width=True)

    if "step1_df" in st.session_state:
        st.success(f"{len(st.session_state['step1_df'])} papers loaded.")
        st.dataframe(st.session_state["step1_df"], use_container_width=True)


# ---------------- STEP 2 ----------------
with tabs[1]:
    st.header("Step 2 — Filter & Select")

    if "step1_df" not in st.session_state:
        st.warning("Run Step 1 first.")
    else:
        selected_df = step2_filter_ui(st.session_state["step1_df"])
        st.dataframe(selected_df, use_container_width=True)


# ---------------- STEP 3 ----------------
with tabs[2]:
    st.header("Step 3 — PDF Download")

    source_option = st.radio("Source of paper list", ["From Step 2", "Upload Excel"])

    if source_option == "Upload Excel":
        uploaded_file = st.file_uploader("Upload Excel", type=["xlsx"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            st.session_state["step2_df"] = df

    if "step2_df" not in st.session_state:
        st.warning("No filtered dataset available.")
    else:
        st.dataframe(st.session_state["step2_df"], use_container_width=True)

        if st.button("Download PDFs"):
            pdfs = download_pdfs(st.session_state["step2_df"])
            st.success(f"{len(pdfs)} PDFs downloaded.")

            zip_buffer = create_zip(pdfs)
            st.download_button(
                "⬇ Download All PDFs (ZIP)",
                data=zip_buffer,
                file_name="downloaded_pdfs.zip",
                mime="application/zip",
            )


# ---------------- STEP 4 ----------------
with tabs[3]:
    st.header("Step 4 — PDF → 1-Pager Summaries")

    pdf_source = st.radio(
        "Select PDF Source",
        ["From Step 3 Downloads", "Upload PDFs"],
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
        st.success(f"{len(pdf_files)} PDFs loaded.")

        if st.button("Generate Summaries"):
            summaries = summarize_pdfs(pdf_files)

            for fname, text in summaries.items():
                st.subheader(fname)
                st.text_area("Summary", text, height=300)

            zip_buffer = create_zip({k: v.encode("utf-8") for k, v in summaries.items()})
            st.download_button(
                "⬇ Download All Summaries (ZIP)",
                data=zip_buffer,
                file_name="paper_summaries.zip",
                mime="application/zip",
            )
