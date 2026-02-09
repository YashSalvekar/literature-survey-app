import requests
import pandas as pd
import time
import re
from datetime import datetime

MIN_YEAR_DEFAULT = 2016
SEMANTIC_PAGE_SIZE = 50
SEMANTIC_MAX_RESULTS = 500
OPENALEX_MAX_RESULTS = 500
ARXIV_MAX_RESULTS = 300

REQUEST_DELAY = 1.0
ARXIV_DELAY = 3.0

USER_AGENT = "AutoLiteratureSurvey/1.0 (mailto:test@example.com)"


# =========================================================
# HELPERS
# =========================================================
def clean_filename(text):
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text)


def normalize_title(title):
    return re.sub(r"\W+", "", title.lower()) if title else None


def normalize_doi_to_url(doi):
    if not doi:
        return None
    doi = doi.lower().strip()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "")
    return f"https://doi.org/{doi}"


def year_is_valid(year, min_year, max_year):
    return year is None or (min_year <= year <= max_year)


def is_review_paper(title):
    return "YES" if title and "review" in title.lower() else "NO"


# =========================================================
# SEMANTIC SCHOLAR
# =========================================================
def search_semantic_scholar(keyword, min_year, max_year):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    results, offset = [], 0

    while offset < SEMANTIC_MAX_RESULTS:
        r = requests.get(
            url,
            params={
                "query": keyword,
                "fields": "title,abstract,year,citationCount,externalIds,url,openAccessPdf,authors,venue,isOpenAccess,referenceCount",
                "limit": SEMANTIC_PAGE_SIZE,
                "offset": offset
            },
            headers={"User-Agent": USER_AGENT},
            timeout=30
        )

        if r.status_code == 429:
            time.sleep(5)
            continue

        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            break

        for item in data:
            year = item.get("year")
            if not year_is_valid(year, min_year, max_year):
                continue

            title = item.get("title")
            review = is_review_paper(title)

            authors = ", ".join(
                a.get("name") for a in (item.get("authors") or []) if a.get("name")
            ) or None

            ext = item.get("externalIds") or {}

            results.append({
                "Paper Title": title,
                "Paper Link": item.get("url"),
                "Publication Year": year,
                "Publication Type": None,
                "Publication Title": item.get("venue"),
                "Author Names": authors,
                "DOI": normalize_doi_to_url(ext.get("DOI")),
                "PDF Link": (item.get("openAccessPdf") or {}).get("url"),
                "Open Access": item.get("isOpenAccess"),
                "Citations Count": item.get("citationCount") or 0,
                "PubMed ID": ext.get("PubMed"),
                "PMC ID": ext.get("PubMedCentral"),
                "References": item.get("referenceCount"),
                "arXiv ID": ext.get("ArXiv"),
                "Source": "SemanticScholar",
                "Abstract": item.get("abstract"),
                "Review": review,
                "Preprint": "NO",
                "arXiv_used": "NO"
            })

        offset += SEMANTIC_PAGE_SIZE
        time.sleep(REQUEST_DELAY)

    return results


# =========================================================
# OPENALEX
# =========================================================
def search_openalex(keyword, min_year, max_year):
    url = "https://api.openalex.org/works"
    results, cursor = [], "*"

    while len(results) < OPENALEX_MAX_RESULTS:
        r = requests.get(
            url,
            params={"search": keyword, "per-page": 50, "cursor": cursor},
            headers={"User-Agent": USER_AGENT},
            timeout=15
        )
        r.raise_for_status()

        data = r.json()

        for item in data.get("results", []):
            year = item.get("publication_year")
            if not year_is_valid(year, min_year, max_year):
                continue

            title = item.get("title")
            review = is_review_paper(title)

            authors = ", ".join(
                a.get("author", {}).get("display_name")
                for a in (item.get("authorships") or [])
                if a.get("author", {}).get("display_name")
            ) or None

            source = (item.get("primary_location") or {}).get("source") or {}

            results.append({
                "Paper Title": title,
                "Paper Link": item.get("id"),
                "Publication Year": year,
                "Publication Type": item.get("type"),
                "Publication Title": source.get("display_name"),
                "Author Names": authors,
                "DOI": normalize_doi_to_url(item.get("doi")),
                "PDF Link": None,
                "Open Access": (item.get("open_access") or {}).get("is_oa"),
                "Citations Count": item.get("cited_by_count") or 0,
                "PubMed ID": None,
                "PMC ID": None,
                "References": item.get("referenced_works_count"),
                "arXiv ID": None,
                "Source": "OpenAlex",
                "Abstract": None,
                "Review": review,
                "Preprint": "NO",
                "arXiv_used": "NO"
            })

        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break

        time.sleep(REQUEST_DELAY)

    return results


# =========================================================
# ARXIV
# =========================================================
def search_arxiv(keyword, min_year, max_year):
    base_url = "https://export.arxiv.org/api/query"
    results, start = [], 0

    while start < ARXIV_MAX_RESULTS:
        r = requests.get(
            base_url,
            params={"search_query": f"all:{keyword}", "start": start, "max_results": 50},
            headers={"User-Agent": USER_AGENT},
            timeout=30
        )

        entries = re.findall(r"<entry>(.*?)</entry>", r.text, re.DOTALL)
        if not entries:
            break

        for e in entries:
            title = re.search(r"<title>(.*?)</title>", e, re.DOTALL)
            summary = re.search(r"<summary>(.*?)</summary>", e, re.DOTALL)
            published = re.search(r"<published>(\d{4})-", e)
            arxiv_id = re.search(r"<id>(.*?)</id>", e)

            year = int(published.group(1)) if published else None
            if not year_is_valid(year, min_year, max_year):
                continue

            url = arxiv_id.group(1) if arxiv_id else None

            results.append({
                "Paper Title": title.group(1).strip() if title else None,
                "Paper Link": url,
                "Publication Year": year,
                "Publication Type": "preprint",
                "Publication Title": "arXiv",
                "Author Names": None,
                "DOI": None,
                "PDF Link": url.replace("/abs/", "/pdf/") if url else None,
                "Open Access": True,
                "Citations Count": 0,
                "PubMed ID": None,
                "PMC ID": None,
                "References": None,
                "arXiv ID": url.split("/")[-1] if url else None,
                "Source": "arXiv",
                "Abstract": re.sub(r"\s+", " ", summary.group(1)) if summary else None,
                "Review": "NO",
                "Preprint": "YES",
                "arXiv_used": "YES"
            })

        start += 50
        time.sleep(ARXIV_DELAY)

    return results


# =========================================================
# DEDUPLICATION
# =========================================================
def merge_records(records):
    merged = {}
    for r in records:
        key = r["DOI"] or normalize_title(r["Paper Title"])
        if not key:
            continue

        if key not in merged:
            merged[key] = r
        else:
            m = merged[key]
            m["Citations Count"] = max(m["Citations Count"], r["Citations Count"])
            for col in m:
                m[col] = m[col] or r[col]
            if r["Preprint"] == "YES":
                m["Preprint"] = "YES"
                m["arXiv_used"] = "YES"

    return list(merged.values())


# =========================================================
# STREAMLIT ENTRYPOINT
# =========================================================
def run_literature_search(query, max_results=200, min_year=2016, max_year=None):
    """
    Public entrypoint used by app.py
    Returns Pandas DataFrame
    """

    if max_year is None:
        max_year = datetime.now().year

    ss = search_semantic_scholar(query, min_year, max_year)
    oa = search_openalex(query, min_year, max_year)
    ax = search_arxiv(query, min_year, max_year)

    df = pd.DataFrame(merge_records(ss + oa + ax))
    df["Citations Count"] = pd.to_numeric(df["Citations Count"], errors="coerce").fillna(0)
    df = df.sort_values("Citations Count", ascending=False).reset_index(drop=True)

    return df
