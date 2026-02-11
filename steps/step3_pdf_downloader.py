import os
import requests
import streamlit as st
import pandas as pd
from time import sleep


def safe_filename(text):
    return "".join(c for c in text if c.isalnum() or c in (" ", "_", "-")).rstrip()


def download_pdfs(df, output_dir="outputs/pdfs", report_path="outputs/pdf_download_report.xlsx", delay=1.5):
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    st.subheader("📥 Step 3 — Download PDFs")

    results = []
    downloaded_paths = []

    progress = st.progress(0)
    total = len(df)

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        record = row.to_dict()

        title = row.get("Paper Title", "paper")
        url = row.get("PDF Link")

        progress.progress(i / total)

        if not url or not isinstance(url, str):
            record["download_status"] = "skipped"
            record["resolved_pdf_url"] = None
            record["failure_reason"] = "Missing PDF link"
            results.append(record)
            st.warning(f"⚠ Skipped: {title}")
            continue

        fname = safe_filename(title)[:120] + ".pdf"
        path = os.path.join(output_dir, fname)

        try:
            r = requests.get(url, timeout=20, stream=True, allow_redirects=True)
            r.raise_for_status()

            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            record["download_status"] = "success"
            record["resolved_pdf_url"] = r.url
            record["failure_reason"] = None

            downloaded_paths.append(path)
            st.success(f"✅ Downloaded: {title}")

        except Exception as e:
            record["download_status"] = "failed"
            record["resolved_pdf_url"] = None
            record["failure_reason"] = str(e)

            st.error(f"❌ Failed: {title} — {e}")

        results.append(record)
        sleep(delay)

    # Save report
    report_df = pd.DataFrame(results)
    report_df.to_excel(report_path, index=False)

    st.info(f"📄 Download report saved to: {report_path}")

    return downloaded_paths, report_df
