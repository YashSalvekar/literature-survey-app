import os
import re
import requests
import streamlit as st
import pandas as pd
from time import sleep
from urllib.parse import urljoin


# =====================================================
# HELPERS
# =====================================================
def safe_filename(text, max_length=150):
    text = re.sub(r"[^\w\s-]", "", str(text))
    text = re.sub(r"\s+", "_", text)
    return text[:max_length]


def session_headers():
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }


def is_pdf_response(resp):
    return "pdf" in resp.headers.get("Content-Type", "").lower()


def extract_pdf_from_html(url):
    r = requests.get(url, headers=session_headers(), timeout=30)
    r.raise_for_status()

    matches = re.findall(r'href="([^"]+\.pdf[^"]*)"', r.text, re.I)
    if not matches:
        return None

    return urljoin(url, matches[0])


def download_binary(url, path):
    session = requests.Session()
    headers = session_headers()

    session.get("https://www.google.com", headers=headers, timeout=10)

    r = session.get(url, headers=headers, timeout=60, allow_redirects=True)
    r.raise_for_status()

    if not is_pdf_response(r):
        raise ValueError("NOT_PDF")

    with open(path, "wb") as f:
        f.write(r.content)

    return r.url


# =====================================================
# MAIN
# =====================================================
def download_pdfs(
    df,
    output_dir="outputs/pdfs",
    report_path="outputs/pdf_download_report.xlsx",
    delay=1.5,
):
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
            record["failure_reason"] = "NO_URL"
            results.append(record)
            st.warning(f"⚠ Skipped: {title}")
            continue

        fname = safe_filename(title)[:120] + ".pdf"
        path = os.path.join(output_dir, fname)

        try:
            # -------------------------------------------------
            # 1️⃣ DIRECT DOWNLOAD
            # -------------------------------------------------
            resolved_url = download_binary(url, path)

            record["download_status"] = "success"
            record["resolved_pdf_url"] = resolved_url
            record["failure_reason"] = "DIRECT"

            downloaded_paths.append(path)
            st.success(f"✅ Downloaded (direct): {title}")

        except Exception:
            try:
                # -------------------------------------------------
                # 2️⃣ HTML SCRAPE FALLBACK
                # -------------------------------------------------
                pdf_url = extract_pdf_from_html(url)
                if not pdf_url:
                    raise RuntimeError("HTML_NO_PDF")

                resolved_url = download_binary(pdf_url, path)

                record["download_status"] = "success"
                record["resolved_pdf_url"] = resolved_url
                record["failure_reason"] = "HTML_SCRAPE"

                downloaded_paths.append(path)
                st.success(f"✅ Downloaded (HTML scrape): {title}")

            except Exception as e:
                record["download_status"] = "failed"
                record["resolved_pdf_url"] = None
                record["failure_reason"] = str(e)

                st.error(f"❌ Failed: {title}")

        results.append(record)
        sleep(delay)

    # -------------------------------------------------
    # SAVE REPORT
    # -------------------------------------------------
    report_df = pd.DataFrame(results)
    report_df.to_excel(report_path, index=False)

    st.info(f"📄 Download report saved to: {report_path}")

    return downloaded_paths, report_df
