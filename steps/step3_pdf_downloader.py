import os
import requests
import streamlit as st
from time import sleep


def safe_filename(text):
    return "".join(c for c in text if c.isalnum() or c in (" ", "_", "-")).rstrip()


def download_pdfs(df, output_dir="outputs/pdfs", delay=1.5):
    os.makedirs(output_dir, exist_ok=True)

    st.subheader("📥 Step 3 — Download PDFs")

    downloaded_paths = []
    progress = st.progress(0)

    total = len(df)

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        title = row.get("Paper Title", "paper")
        url = row.get("PDF Link")

        progress.progress(i / total)

        if not url or not isinstance(url, str):
            st.warning(f"⚠ No PDF link: {title}")
            continue

        fname = safe_filename(title)[:120] + ".pdf"
        path = os.path.join(output_dir, fname)

        try:
            r = requests.get(url, timeout=20, stream=True)
            r.raise_for_status()

            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            downloaded_paths.append(path)
            st.success(f"✅ Downloaded: {title}")

        except Exception as e:
            st.error(f"❌ Failed: {title} — {e}")

        sleep(delay)

    return downloaded_paths
