import os
import re
import time
import requests
import pandas as pd


def clean_filename(text, max_length=150):
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

    matches = re.findall(r'href="([^"]+\.pdf[^"]*)"', r.text, re.I)
    if not matches:
        return None

    from urllib.parse import urljoin
    return urljoin(url, matches[0])


def run_pdf_download(df, output_dir="outputs/pdfs", delay=2):
    os.makedirs(output_dir, exist_ok=True)

    results = []

    for i, row in df.iterrows():
        title = clean_filename(row.get("Paper Title"))
        year = row.get("Publication Year", "NA")
        filename = f"{i+1:03d}_{year}_{title}.pdf"
        filepath = os.path.join(output_dir, filename)

        url = row.get("PDF Link")
        status = "FAILED"
        resolved_url = None
        reason = None

        if not url or not isinstance(url, str):
            results.append({**row, "download_status": "NO_URL"})
            continue

        try:
            download_pdf(url, filepath)
            status = "DOWNLOADED"
            resolved_url = url
            reason = "DIRECT"

        except Exception:
            try:
                pdf_url = extract_pdf_from_html(url)
                if not pdf_url:
                    raise Exception("HTML_NO_PDF")

                download_pdf(pdf_url, filepath)
                status = "DOWNLOADED"
                resolved_url = pdf_url
                reason = "HTML_SCRAPE"

            except Exception:
                status = "FAILED"
                resolved_url = url
                reason = "BLOCKED_OR_UNKNOWN"

        results.append({
            **row,
            "download_status": status,
            "resolved_pdf_url": resolved_url,
            "failure_reason": reason,
            "local_pdf_path": filepath if status == "DOWNLOADED" else None
        })

        time.sleep(delay)

    return pd.DataFrame(results)
