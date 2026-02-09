import streamlit as st
from groq import Groq
from utils.pdf_utils import extract_text_from_pdf_bytes


def get_groq_client():
    if "GROQ_API_KEY" not in st.secrets:
        raise RuntimeError("Missing GROQ_API_KEY in Streamlit secrets.")
    return Groq(api_key=st.secrets["GROQ_API_KEY"])


def summarize_pdfs(pdf_files_dict):
    st.subheader("Step 4 — Generate 1-Pager Summaries")

    client = get_groq_client()
    summaries = {}

    for fname, pdf_bytes in pdf_files_dict.items():
        text = extract_text_from_pdf_bytes(pdf_bytes)

        prompt = f"""
Create a 1-page structured literature summary with:
- Problem
- Methodology
- Dataset
- Key Findings
- Limitations
- Future Work

Text:
{text[:12000]}
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        summary = response.choices[0].message.content
        summaries[fname.replace(".pdf", ".txt")] = summary

    st.session_state["summaries"] = summaries
    return summaries
