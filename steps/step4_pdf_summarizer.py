import os
import time
import re
import fitz  # PyMuPDF
from groq import Groq
from docx import Document
from tqdm import tqdm
import streamlit as st

MODEL_NAME = "llama-3.1-8b-instant"

TPM_LIMIT = 6000
TPM_BUFFER = 600
CHARS_PER_TOKEN = 4

CHUNK_INPUT_TOKENS = 2000
MAX_OUTPUT_TOKENS_CHUNK = 300
MAX_OUTPUT_TOKENS_INTERMEDIATE = 400
MAX_OUTPUT_TOKENS_FINAL = 800

MAX_CHARS_PER_CHUNK = CHUNK_INPUT_TOKENS * CHARS_PER_TOKEN

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

TOKENS_USED = 0
WINDOW_START = time.time()

# ==========================================================
# TOKEN / TPM GUARD
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
# PDF UTILITIES
# ==========================================================
def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text() for page in doc).strip()

def extract_pdf_title(pdf_path):
    doc = fitz.open(pdf_path)
    lines = doc[0].get_text().split("\n")
    for line in lines:
        if line.strip() and len(line.strip()) > 12:
            return line.strip()
    return os.path.basename(pdf_path).replace(".pdf", "")

def chunk_text(text):
    return [
        text[i:i + MAX_CHARS_PER_CHUNK]
        for i in range(0, len(text), MAX_CHARS_PER_CHUNK)
    ]

# ==========================================================
# WORD SANITIZATION
# ==========================================================
def clean_for_word(text):
    text = text.replace("\x00", "")
    text = re.sub(r"[\x01-\x08\x0B\x0C\x0E-\x1F]", "", text)
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    return text

# ==========================================================
# STAGE 1 — MAP
# ==========================================================
def summarize_chunk(chunk):
    prompt = f"""
Extract concise factual technical notes from the text below.

Rules:
- Only extract information explicitly stated
- No title, no conclusions
- No interpretation or external knowledge
- Avoid repetition
- Compact bullet-style notes

Text:
{chunk}
"""
    est_tokens = estimate_tokens(chunk) + MAX_OUTPUT_TOKENS_CHUNK
    tpm_guard(est_tokens)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=MAX_OUTPUT_TOKENS_CHUNK
    )

    return response.choices[0].message.content.strip()

# ==========================================================
# STAGE 2 — INTERMEDIATE REDUCE
# ==========================================================
def reduce_notes_in_batches(notes, batch_size=3):
    reduced = []

    for i in range(0, len(notes), batch_size):
        batch = "\n".join(notes[i:i + batch_size])

        prompt = f"""
Condense the following technical notes into a single compact factual summary.
Do NOT add new information.

Notes:
{batch}
"""
        est_tokens = estimate_tokens(batch) + MAX_OUTPUT_TOKENS_INTERMEDIATE
        tpm_guard(est_tokens)

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=MAX_OUTPUT_TOKENS_INTERMEDIATE
        )

        reduced.append(response.choices[0].message.content.strip())

    return reduced

# ==========================================================
# STAGE 3 — FINAL ONE-PAGER
# ==========================================================
def generate_one_pager(pdf_title, notes):
    prompt = f"""
You are an expert scientific reviewer preparing structured literature-review notes
for a SINGLE research paper.

STRICT RULES:
- Use ONLY the provided content
- Do NOT invent references, authors, or years
- If information is missing, omit that section
- Title MUST match exactly

──────────── FORMAT ────────────

Title:
{pdf_title}

Reference:
<Authors, journal, year — ONLY if explicitly stated>

Research Objective / Scope:
<1–3 sentences>

Methods / Approach:
- Key methodological choices only

Key Results / Observations:
- Most important quantitative or qualitative outcomes

Key Contributions / Novelty:
<What this work enables or improves>

Limitations / Assumptions:
<Only if stated>

Implications / Applications:
<Grounded in results>

Future Directions:
<Only if explicitly mentioned>

──────────── CONTENT ────────────
{notes}
"""
    est_tokens = estimate_tokens(notes) + MAX_OUTPUT_TOKENS_FINAL + 600
    tpm_guard(est_tokens)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=MAX_OUTPUT_TOKENS_FINAL
    )

    return response.choices[0].message.content.strip()

# ==========================================================
# SAVE WORD FILE
# ==========================================================
def save_word(text, output_path):
    text = clean_for_word(text)
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    doc.save(output_path)

# ==========================================================
# PUBLIC API (USED BY STREAMLIT)
# ==========================================================
def summarize_pdfs(pdf_dir, output_dir="outputs/summaries"):
    os.makedirs(output_dir, exist_ok=True)

    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
    results = {}

    for pdf in tqdm(pdf_files, desc="Processing PDFs"):
        pdf_path = os.path.join(pdf_dir, pdf)
        raw_text = extract_pdf_text(pdf_path)

        if len(raw_text) < 3000:
            continue

        title = extract_pdf_title(pdf_path)
        chunks = chunk_text(raw_text)

        # MAP
        notes = [summarize_chunk(chunk) for chunk in chunks]

        # INTERMEDIATE REDUCE
        reduced_notes = reduce_notes_in_batches(notes, batch_size=3)

        # FINAL REDUCE
        final_notes = "\n".join(reduced_notes)
        one_pager = generate_one_pager(title, final_notes)

        output_path = os.path.join(
            output_dir,
            pdf.replace(".pdf", "_one_pager.docx")
        )

        save_word(one_pager, output_path)
        results[pdf] = one_pager

    return results
