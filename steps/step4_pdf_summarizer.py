import os
import time
import re
import fitz
import streamlit as st
from groq import Groq
from docx import Document

# ==========================================================
# CONFIG
# ==========================================================
MODEL_NAME = "llama-3.1-8b-instant"

TPM_LIMIT = 6000
TPM_BUFFER = 600
CHARS_PER_TOKEN = 4

CHUNK_INPUT_TOKENS = 2000
MAX_OUTPUT_TOKENS_CHUNK = 300
MAX_OUTPUT_TOKENS_INTERMEDIATE = 400
MAX_OUTPUT_TOKENS_FINAL = 800

MAX_CHARS_PER_CHUNK = CHUNK_INPUT_TOKENS * CHARS_PER_TOKEN

TOKENS_USED = 0
WINDOW_START = time.time()


# ==========================================================
# TOKEN GUARD
# ==========================================================
def estimate_tokens(text):
    return max(1, len(text) // CHARS_PER_TOKEN)


def tpm_guard(estimated_tokens):
    global TOKENS_USED, WINDOW_START

    now = time.time()
    elapsed = now - WINDOW_START

    if elapsed >= 60:
        TOKENS_USED = 0
        WINDOW_START = now

    if TOKENS_USED + estimated_tokens > (TPM_LIMIT - TPM_BUFFER):
        sleep_time = max(1, 60 - elapsed)
        time.sleep(sleep_time)
        TOKENS_USED = 0
        WINDOW_START = time.time()

    TOKENS_USED += estimated_tokens


# ==========================================================
# METADATA
# ==========================================================
def extract_title_and_authors_from_bytes(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    text = page.get_text()
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    title = lines[0] if lines else "Unknown Title"
    authors = lines[1] if len(lines) > 1 else "Not explicitly detected"

    return title, authors


# ==========================================================
# TEXT EXTRACTION
# ==========================================================
def extract_pdf_text_from_bytes(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc).strip()


def chunk_text(text):
    return [
        text[i:i + MAX_CHARS_PER_CHUNK]
        for i in range(0, len(text), MAX_CHARS_PER_CHUNK)
    ]


# ==========================================================
# LLM STAGES
# ==========================================================
def summarize_chunk(client, chunk):
    prompt = f"""
Extract concise factual technical notes from the text below.

Rules:
- Only extract information explicitly stated
- No title, no conclusions
- No interpretation
- Avoid repetition
- Compact bullet-style notes

Text:
{chunk}
"""
    est = estimate_tokens(chunk) + MAX_OUTPUT_TOKENS_CHUNK
    tpm_guard(est)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=MAX_OUTPUT_TOKENS_CHUNK
    )

    return response.choices[0].message.content.strip()


def reduce_notes(client, notes):
    batch = "\n".join(notes)

    prompt = f"""
Condense the following technical notes into a compact factual summary.
Do NOT add new information.

Notes:
{batch}
"""

    est = estimate_tokens(batch) + MAX_OUTPUT_TOKENS_INTERMEDIATE
    tpm_guard(est)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=MAX_OUTPUT_TOKENS_INTERMEDIATE
    )

    return response.choices[0].message.content.strip()


def generate_one_pager(client, title, authors, notes):
    prompt = f"""
Title:
{title}

References:
{authors}

Create a structured 1-page research summary using ONLY the provided content.
Be concise and factual.

CONTENT:
{notes}
"""

    est = estimate_tokens(notes) + MAX_OUTPUT_TOKENS_FINAL
    tpm_guard(est)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=MAX_OUTPUT_TOKENS_FINAL
    )

    return response.choices[0].message.content.strip()


# ==========================================================
# WORD SAVE
# ==========================================================
def save_word(text, output_path):
    doc = Document()
    for line in text.split("\n"):
        if line.strip():
            doc.add_paragraph(line.strip())
    doc.save(output_path)


# ==========================================================
# MAIN ENTRY FOR STREAMLIT
# ==========================================================
def summarize_pdfs(pdf_files, output_dir="outputs/summaries"):
    os.makedirs(output_dir, exist_ok=True)

    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    summaries = {}
    progress = st.progress(0)
    total = len(pdf_files)

    for i, (fname, pdf_bytes) in enumerate(pdf_files.items(), start=1):
        progress.progress(i / total)

        try:
            raw_text = extract_pdf_text_from_bytes(pdf_bytes)

            if len(raw_text) < 3000:
                st.warning(f"Skipping {fname} (too short)")
                continue

            title, authors = extract_title_and_authors_from_bytes(pdf_bytes)

            chunks = chunk_text(raw_text)
            notes = [summarize_chunk(client, c) for c in chunks]
            reduced = reduce_notes(client, notes)

            one_pager = generate_one_pager(client, title, authors, reduced)

            output_path = os.path.join(
                output_dir,
                fname.replace(".pdf", "_one_pager.docx")
            )

            save_word(one_pager, output_path)

            summaries[fname] = one_pager
            st.success(f"✅ Completed: {fname}")

        except Exception as e:
            st.error(f"❌ Failed: {fname} — {e}")

    return summaries
