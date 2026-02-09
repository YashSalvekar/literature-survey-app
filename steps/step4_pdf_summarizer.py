import os
import re
import time
import fitz  # PyMuPDF
from docx import Document
import streamlit as st

try:
    from groq import Groq
except ImportError:
    Groq = None


MODEL_NAME = "llama-3.1-8b-instant"
CHARS_PER_TOKEN = 4
MAX_CHARS_PER_CHUNK = 2000 * CHARS_PER_TOKEN
MAX_OUTPUT_TOKENS = 800


def get_groq_client():
    if "GROQ_API_KEY" not in st.secrets:
        raise RuntimeError(
            "❌ GROQ_API_KEY missing. Add it in Streamlit Cloud → Manage app → Settings → Secrets."
        )
    return Groq(api_key=st.secrets["GROQ_API_KEY"])


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


def clean_for_word(text):
    text = text.replace("\x00", "")
    text = re.sub(r"[\x01-\x08\x0B\x0C\x0E-\x1F]", "", text)
    return text


def summarize_text(client, title, text):
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
{title}

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
{text}
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=MAX_OUTPUT_TOKENS
    )
    return response.choices[0].message.content.strip()


def save_word(text, output_path):
    text = clean_for_word(text)
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    doc.save(output_path)


def run_pdf_summarization(pdf_dir, output_dir="outputs/summaries"):
    os.makedirs(output_dir, exist_ok=True)
    client = get_groq_client()

    results = []

    for filename in os.listdir(pdf_dir):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(pdf_dir, filename)
        raw_text = extract_pdf_text(pdf_path)

        if len(raw_text) < 3000:
            continue

        title = extract_pdf_title(pdf_path)
        summary = summarize_text(client, title, raw_text)

        output_path = os.path.join(output_dir, filename.replace(".pdf", "_one_pager.docx"))
        save_word(summary, output_path)

        results.append({
            "pdf_file": filename,
            "summary_path": output_path
        })

    return results
