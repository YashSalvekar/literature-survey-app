import os
import requests
import streamlit as st
import pandas as pd
from time import sleep
from urllib.parse import urljoin
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "application/pdf,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
}


def safe_filename(text):
    return "".join(c for c in text if c.isalnum() or c in (" ", "_", "-")).rstrip()


def looks_like_pdf_response(resp):
    ctype = resp.headers.get("Content-Type", "").lower()
    return "application/pdf" in ctype or resp.url.lower().endswith(".pdf")


def try_direct_download(url, path):
    r = requests.get(url, headers=HEADERS, timeout=25, stream=True, allow_redirects=True)
    r.raise_for_status()

    if not looks_like_pdf_response(r):
        return None, "NOT_PDF_RESPONSE", r.url

    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return path, "DIRECT", r.url


def extract_pdf_from_html(html, base_url):
    soup = BeautifulSoup(html, "html.parser")

    # 1️⃣ Meta tag (Elsevier, Springer, Nature, etc.)
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return urljoin(base_url, meta["content"])

    # 2️⃣ Any link/embed containing .pdf
    for tag in soup.find_all(["a", "iframe", "embed"]):
        href = tag.get("href") or tag.get("src")
        if href and ".pdf" in href.lower():
            return urljoin(base_url, href)

    # 3️⃣ Script-based URLs
    for script in soup.find_all("script"):
        if script.string:
            matches = re.findall(r"https?://[^\s\"']+\.pdf", script.string)
            if matches:
                return matches[0]

    return None


def try_html_fallback(url):
    r = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
    r.raise_for_status()

    pdf_url = extract_pdf_from_html(r.text, r.url)
    if not pdf_url:
        return None, "HTML_NO_PDF"

    return pdf_url, "HTML_EXTRACTED"


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
            record["resolved_pdf_url"] = "NO_URL"
            record["failure_reason"] = "Missing PDF link"
            results.append(record)
            st.warning(f"⚠ Skipped: {title}")
            continue

        fname = safe_filename(title)[:120] + ".pdf"
        path = os.path.join(output_dir, fname)

        try:
            # ---------- 1️⃣ Direct download ----------
            direct_path, mode, final_url = try_direct_download(url, path)
            if direct_path:
                record["download_status"] = "success"
                record["resolved_pdf_url"] = final_url
                record["failure_reason"] = mode
                downloaded_paths.append(path)
                results.append(record)
                st.success(f"✅ Downloaded: {title}")
                sleep(delay)
                continue

            # ---------- 2️⃣ HTML fallback ----------
            pdf_url, reason = try_html_fallback(url)
            if not pdf_url:
                raise Exception(reason)

            direct_path, mode, final_url = try_direct_download(pdf_url, path)
            if not direct_path:
                raise Exception("FALLBACK_PDF_DOWNLOAD_FAILED")

            record["download_status"] = "success"
            record["resolved_pdf_url"] = final_url
            record["failure_reason"] = mode
            downloaded_paths.append(path)
            st.success(f"✅ Downloaded (HTML): {title}")

        except Exception as e:
            record["download_status"] = "failed"
            record["resolved_pdf_url"] = None
            record["failure_reason"] = str(e)
            st.error(f"❌ Failed: {title} — {e}")

        results.append(record)
        sleep(delay)

    report_df = pd.DataFrame(results)
    report_df.to_excel(report_path, index=False)

    st.info(f"📄 Download report saved to: {report_path}")

    return downloaded_paths, report_df
