import requests
import streamlit as st


def download_pdfs(df):
    st.subheader("Step 3 — Download PDFs")

    downloaded_files = {}

    for _, row in df.iterrows():
        title = row.get("title", "paper").replace("/", "_")
        url = row.get("pdf_url")

        if not url:
            continue

        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            downloaded_files[f"{title}.pdf"] = resp.content
            st.success(f"Downloaded: {title}")
        except Exception as e:
            st.warning(f"Failed: {title} — {e}")

    st.session_state["downloaded_pdfs"] = downloaded_files
    return downloaded_files
