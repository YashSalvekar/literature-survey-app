import os
import re
import time
import requests
import streamlit as st
import pandas as pd
from urllib.parse import urljoin


# =====================================================
# UTILITIES
# =====================================================
def safe_filename(text, max_length=140):
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


# =====================================================
# DOWNLOAD METHODS
# =====================================================
def download_pdf_direct(url, filepath):
    session = requests.Session()
    headers = session_headers()

    # warmup
    session.get("https://www.google.com", headers=headers, timeout=10)

    r = session.get(url, headers=headers, timeout=60, allow_redirects=True)
    r.raise_for_status()

    if "pdf" not in r.headers.get("Content-Type", "").lower():
        raise ValueError("NOT_PDF")

    with open(filepath, "wb") as f:
        f.write(r.content)

    return r.url


def extract_pdf_from_html(url):
    r = requests.get(url, headers=session_headers(), timeout=30)
    r.raise_for_status()

    pdf_links = re.findall(r'href="([^"]+\.pdf[^"]*)"', r.text, re.I)
    if not pdf_links:
        return None

    return urljoin(url, pdf_links[0])


# Optional selenium fallback (only if enabled)
def selenium_download(url, filepath):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(5)

    links = driver.find_elements(By.XPATH, "//a[contains(@href,'.pdf')]")
    if not links:
        driver.quit()
        raise RuntimeError("NO_PDF_FOUND")

    pdf_url = links[0].get_attribute("href")
    driver.quit()

    resolved = download_pdf_direct(pdf_url, filepath)
    return resolved


# =====================================================
# MAIN STREAMLIT FUNCTION
# =====================================================
def download_pdfs(
    df,
    output_dir="outputs/pdfs",
    report_path="outputs/pdf_download_report.xlsx",
    delay=1.5,
    use_selenium=False,
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
            record["failure_reason"] = "Missing PDF link"
            results.append(record)
            st.warning(f"⚠ Skipped: {title}")
            continue

        fname = safe_filename(title)[:120] + ".pdf"
        path = os.path.join(output_dir, fname)

        try:
            # ---------- 1️⃣ Direct PDF ----------
            resolved = download_pdf_direct(url, path)

            record["download_status"] = "success"
            record["resolved_pdf_url"] = resolved
            record["failure_reason"] = "DIRECT"

            downloaded_paths.append(path)
            st.success(f"✅ Downloaded: {title}")

        except Exception:
            try:
                # ---------- 2️⃣ HTML scrape ----------
                pdf_url = extract_pdf_from_html(url)
                if not pdf_url:
                    raise Exception("HTML_NO_PDF")

                resolved = download_pdf_direct(pdf_url, path)

                record["download_status"] = "success"
                record["resolved_pdf_url"] = resolved
                record["failure_reason"] = "HTML_SCRAPE"

                downloaded_paths.append(path)
                st.success(f"✅ Downloaded (HTML): {title}")

            except Exception:
                if use_selenium:
                    try:
                        # ---------- 3️⃣ Selenium fallback ----------
                        resolved = selenium_download(url, path)

                        record["download_status"] = "success"
                        record["resolved_pdf_url"] = resolved
                        record["failure_reason"] = "SELENIUM"

                        downloaded_paths.append(path)
                        st.success(f"✅ Downloaded (Selenium): {title}")

                    except Exception:
                        record["download_status"] = "failed"
                        record["resolved_pdf_url"] = None
                        record["failure_reason"] = classify_failure(url)
                        st.error(f"❌ Failed: {title}")

                else:
                    record["download_status"] = "failed"
                    record["resolved_pdf_url"] = None
                    record["failure_reason"] = classify_failure(url)
                    st.error(f"❌ Failed: {title}")

        results.append(record)
        time.sleep(delay)

    # =====================================================
    # SAVE REPORT
    # =====================================================
    report_df = pd.DataFrame(results)
    report_df.to_excel(report_path, index=False)

    st.info(f"📄 Download report saved to: {report_path}")

    return downloaded_paths, report_df
