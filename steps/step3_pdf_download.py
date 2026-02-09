import pandas as pd
import requests
import os
import re
import time
from urllib.parse import urljoin

REQUEST_DELAY = 2

# =========================================================
# UTILITIES
# =========================================================
def clean_filename(text, max_length=150):
    text = re.sub(r"[^\w\s-]", "", str(text))
    text = re.sub(r"\s+", "_", text)
    return text[:max_length]

def classify_failure(url):
    if not url:
        return "NO_URL"
    if "mdpi.com" in url:
        return "MDPI"
    if "wiley.com" in url:
        return "Wiley"
    if "sagepub.com" in url:
        return "SAGE"
    if "springer.com" in url:
        return "Springer"
    return "OTHER"

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

# =========================================================
# DOWNLOAD METHODS
# =========================================================
def download_pdf(url, filepath):
    session = requests.Session()
    headers = session_headers()

    session.get("https://www.google.com", headers=headers, timeout=10)

    r = session.get(url, headers=headers, timeout=60, allow_redirects=True)
    r.raise_for_status()

    if "pdf" not in r.headers.get("Content-Type", "").lower():
        raise ValueError("NOT_PDF")

    with open(filepath, "wb") as f:
        f.write(r.content)

def extract_pdf_from_html(url):
    r = requests.get(url, headers=session_headers(), timeout=30)
    r.raise_for_status()

    pdf_links = re.findall(r'href="([^"]+\.pdf[^"]*)"', r.text, re.I)
    if not pdf_links:
        return None

    return urljoin(url, pdf_links[0])

# =========================================================
# PUBLIC API (USED BY STREAMLIT)
# =========================================================
def download_pdfs(df, output_dir="data/downloaded_pdfs", only_reviews=False, top_n=None):
    os.makedirs(output_dir, exist_ok=True)

    for col in ["resolved_pdf_url", "status", "failure_reason"]:
        if col not in df.columns:
            df[col] = ""

    df_targets = df[
        (df["PDF Link"].notna()) &
        (df["PDF Link"].astype(str).str.strip() != "")
    ]

    if only_reviews:
        df_targets = df_targets[df_targets["Review"] == "YES"]

    df_targets = df_targets.sort_values("Citations Count", ascending=False)

    if top_n is not None:
        df_targets = df_targets.head(top_n)

    results = []

    for i, (idx, row) in enumerate(df_targets.iterrows(), start=1):
        title = clean_filename(row["Paper Title"])
        year = row["Publication Year"] if not pd.isna(row["Publication Year"]) else "NA"
        filename = f"{i:03d}_{year}_{title}.pdf"
        filepath = os.path.join(output_dir, filename)

        url = row["PDF Link"]
        df.at[idx, "resolved_pdf_url"] = url

        try:
            download_pdf(url, filepath)
            df.at[idx, "status"] = "DOWNLOADED"
            df.at[idx, "failure_reason"] = "DIRECT"
            results.append(filepath)

        except Exception:
            try:
                pdf_url = extract_pdf_from_html(url)
                if not pdf_url:
                    raise Exception("HTML_NO_PDF")

                df.at[idx, "resolved_pdf_url"] = pdf_url
                download_pdf(pdf_url, filepath)

                df.at[idx, "status"] = "DOWNLOADED"
                df.at[idx, "failure_reason"] = "HTML_SCRAPE"
                results.append(filepath)

            except Exception:
                df.at[idx, "status"] = "FAILED"
                df.at[idx, "failure_reason"] = classify_failure(url)

        time.sleep(REQUEST_DELAY)

    return results, df
