[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/vgbm4cZ0)

# ADGM Corporate Agent

A fast, AI-powered reviewer for Abu Dhabi Global Market (ADGM) corporate documents. Upload .docx files, get actionable inline comments, and a clean JSON report—grounded in official ADGM sources.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)

This project was developed as a take-home assignment for the AI Engineer Intern position at 2Cents Capital. It is a production-grade solution that meets core requirements outlined in the task sheet.

## 🚀 Live Demo
Drive Link : [https://drive.google.com/file/d/1U_P-ZB-bjOkaaRwbRkyO3jvuoggIHfJW/view?usp=sharing]

> Screenshots
> <img width="1582" height="967" alt="Screenshot 2025-08-11 at 10 00 55 AM" src="https://github.com/user-attachments/assets/67370919-01b9-401b-9e53-463ad396b2be" />
> <img width="1582" height="967" alt="Screenshot 2025-08-11 at 10 01 26 AM" src="https://github.com/user-attachments/assets/7ab52d64-2840-49df-b3ac-d6682425b16b" />
> <img width="1582" height="967" alt="Screenshot 2025-08-11 at 10 02 51 AM" src="https://github.com/user-attachments/assets/733b04a4-8655-4c9b-9bd8-15be9b4b6462" />
> <img width="1582" height="967" alt="Screenshot 2025-08-11 at 10 03 01 AM" src="https://github.com/user-attachments/assets/04080f3f-b840-4440-bf4f-f5a1869f792e" />
> <img width="1582" height="967" alt="Screenshot 2025-08-11 at 10 04 07 AM" src="https://github.com/user-attachments/assets/477a96c6-d17c-4377-86f4-3ea902f085d9" />
> <img width="1582" height="967" alt="Screenshot 2025-08-11 at 10 04 14 AM" src="https://github.com/user-attachments/assets/0dfb7a77-f310-4908-b058-38e7c856eef9" />
> <img width="1582" height="967" alt="Screenshot 2025-08-11 at 10 21 59 AM" src="https://github.com/user-attachments/assets/e707d0f3-65d4-4341-aa14-9447071de3a1" />
> <img width="1527" height="967" alt="Screenshot 2025-08-11 at 10 22 43 AM" src="https://github.com/user-attachments/assets/4f6e2217-70f8-486c-aee6-8ee899084e76" />



### Why this matters
Preparing filings for Abu Dhabi Global Market (ADGM) can be tedious: many document types, process checklists, and subtle compliance rules. Manual review is slow and error-prone—especially for teams working under deadlines.

### What this project solves
The ADGM Corporate Agent analyzes .docx legal documents, checks them against ADGM regulations and templates, and returns:

- A reviewed .docx with inline comments at relevant clauses
- A structured JSON report summarizing findings and missing items
- An optional Q&A panel that explains issues using a RAG knowledge base

---

## Solution overview
- Upload one or more .docx files (AoA, resolutions, employment contracts, etc.)
- The app classifies document types, infers the process (e.g., Company Incorporation), verifies required documents, and runs compliance checks
- Retrieval-Augmented Generation (RAG) fetches relevant ADGM passages; Gemini 1.5 Flash produces concise, cited issues (with rule-based fallbacks)
- Results: inline comments + JSON summary + a ZIP bundle for download

## Key features
- Document parsing and type detection
- Process inference + checklist gap analysis (e.g., required registers for incorporation)
- RAG over your local ADGM sources (PDF/HTML/DOCX) with embeddings (Chroma + sentence-transformers)
- Gemini-powered clause checks (fallback rule-based checks for reliability)
- Inline .docx comments (styled markers) that don’t alter original content
- Clean JSON report, plus a ZIP bundling all reviewed documents
- Optional Q&A panel using the same RAG knowledge base

---

## Installation & setup

### Prerequisites
- Python 3.10+
- macOS/Linux/Windows

### 1) Clone and install
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Environment variables
Create a `.env` (copy from `.env.example`) and set:
```bash
APP_ENV=local
LLM_PROVIDER=gemini            # or ollama, etc.
GEMINI_API_KEY=YOUR_KEY_HERE   # required if LLM_PROVIDER=gemini
OLLAMA_HOST=http://localhost:11434

# Inline comments metadata
COMMENT_AUTHOR=ADGM Corporate Agent
COMMENT_INITIALS=AA
```

### 3) Add ADGM sources (RAG)
Place PDFs/HTML/DOCX under `data/adgm_sources/` and define them in `data/sources_manifest.json`. Then build the index from the app (sidebar → Advanced → Build/Refresh Index).

---

## Usage

### Start the app
```bash
streamlit run src/agent/ui/app.py
```

### Analyze documents
1) Upload one or more `.docx` files
2) Keep “Insert inline comments” enabled (recommended)
3) Select Intended process (optional) if you want specific checklists
4) Click “Run Analysis”
5) Review per-file issues, process summary, and download:
   - Reviewed .docx with comments
   - `adgm_report.json`
   - One-click ZIP bundling everything

### Q&A (optional)
- Expand “Q&A (optional)”
- Select a context document (optional)
- Ask a question (e.g., “Why was the jurisdiction clause flagged?”)
- The agent answers with concise reasoning and citations

---

## Examples
Minimal programmatic usage (classification + parsing):
```python
from agent.doc_processing.parser import load_document_from_bytes, parse_document_structure
from agent.classification.classifier import DocumentClassifier

with open("sample.docx", "rb") as f:
    doc = load_document_from_bytes(f.read())

blocks = parse_document_structure(doc)
label = DocumentClassifier().classify("sample.docx", doc)
print(label, blocks[:3])
```

---

## Project structure
```text
ADGM-Corporate_Agent/
├─ src/
│  ├─ agent/
│  │  ├─ analysis/           # RAG+LLM checks and fallbacks
│  │  ├─ chat/               # Q&A over RAG
│  │  ├─ classification/     # Document type detection
│  │  ├─ doc_processing/     # Parsing + inline annotations
│  │  ├─ knowledge/          # Sources manifest loader
│  │  ├─ process/            # Process inference + checklists
│  │  ├─ rag/                # Ingestion + retrieval (Chroma)
│  │  ├─ reporting/          # JSON report models
│  │  └─ ui/                 # Streamlit app
├─ data/
│  ├─ adgm_sources/          # Your ADGM PDFs/HTML/DOCX
│  └─ sources_manifest.json  # Source registry
├─ input/                    # Place .docx for batch mode
├─ output/                   # reviewed docs + report.json
├─ requirements.txt
├─ .env.example
└─ README.md
```

---

## Tech stack
- Streamlit (UI)
- python-docx (parse + annotate .docx)
- Google Gemini 1.5 Flash (LLM, optional)
- Sentence-Transformers + Chroma (RAG)
- PyPDF / BeautifulSoup (PDF/HTML parsing)
- Pydantic (report schema)

---

## Disclaimer & evaluation use
- For recruitment/selection process evaluation. Not for production.
- No legal advice: Outputs reference ADGM sources but are informational.
- Sensitive documents: The app processes files in-memory; do not upload confidential data unless permitted by your organization.

---

## License
This work is provided for evaluation purposes only (non-commercial, non-production). Rights remain with the commissioning organization. Do not redistribute without permission.

---

## 📬 Contact Me

- **LinkedIn**: [Dhruv Suvagiya](https://www.linkedin.com/in/dhruv-suvagiya/)
- **GitHub**: [Dhruv-2004](https://github.com/Dhruv-2004)
- **Email**: [dhruvsuvagiya21@gmail.com](mailto:dhruvsuvagiya21@gmail.com)

---
