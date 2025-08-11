from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import re

from docx import Document

from agent.llm.gemini_client import GeminiClient
from agent.rag.ingest import query_improved
from agent.reporting.report import Issue


def _summarize_doc(doc: Document, max_chars: int = 12000) -> str:
    text = "\n".join(p.text for p in doc.paragraphs)
    return text[:max_chars]


def _ask_gemini_for_issues(document_text: str, retrieved_passages: List[Dict[str, str]], doc_type: str) -> List[Issue]:
    gemini = GeminiClient()
    if not gemini.enabled or not getattr(gemini, "model", None):
        return []

    refs_str = "\n\n".join([
        f"[Source: {r.get('title','')}; {r.get('citation','')}]\n{r['text']}" for r in retrieved_passages
    ])

    prompt = (
        "You are an ADGM legal compliance checker. Using the retrieved ADGM sources, "
        "identify concrete red flags in the document. Cite the exact ADGM rule in parentheses.\n\n"
        f"Document type: {doc_type}\n\n"
        "Document (excerpt):\n" + document_text + "\n\n"
        "Retrieved ADGM references:\n" + refs_str + "\n\n"
        "Respond in JSON array of objects with keys: section (optional), issue, severity (High/Medium/Low), suggestion."
    )

    try:
        resp = gemini.model.generate_content(prompt)
        text = getattr(resp, "text", "").strip()
        # Gemini may return markdown code block; try to extract JSON
        import json, re
        match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        data = json.loads(text)
        issues: List[Issue] = []
        for item in data if isinstance(data, list) else []:
            issues.append(
                Issue(
                    document="",
                    section=item.get("section"),
                    issue=item.get("issue", ""),
                    severity=item.get("severity", "Medium"),
                    suggestion=item.get("suggestion"),
                )
            )
        return issues
    except Exception:
        return []


def _paragraph_starts_with_number(text: str) -> bool:
    # Matches: "1.", "1)", "1 -", "1 –", "1:"
    return re.match(r"^\s*\d+\s*(\.|\)|-|–|:)\s+", text) is not None


def _has_sequential_numbered_paragraphs(doc: Document, min_count: int = 3) -> bool:
    count = 0
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        if _paragraph_starts_with_number(t):
            count += 1
            if count >= min_count:
                return True
    return False


def analyze_document(doc: Document, filename: str, doc_type: str) -> List[Issue]:
    issues: List[Issue] = []

    # Build RAG query tailored to the doc type
    if doc_type == "Employment Contract":
        query = "ADGM Employment Regulations 2024 mandatory employment contract terms and governing law clause"
        scopes = ["Employment Contracts"]
    elif doc_type == "Articles of Association":
        query = "ADGM Companies Regulations 2020 Articles of Association must be in a single document and paragraphs numbered consecutively"
        scopes = ["AoA", "Company Incorporation"]
    else:
        query = "ADGM model jurisdiction clause governed by ADGM law and ADGM Courts"
        scopes = ["Jurisdiction/Choice-of-Law"]

    retrieved = []
    try:
        retrieved = query_improved(query_text=query, top_k=5, pre_k=30, filter_scopes=scopes)
    except Exception:
        pass

    doc_text = _summarize_doc(doc)

    # Ask Gemini for issues using RAG context (if available)
    llm_issues = _ask_gemini_for_issues(doc_text, retrieved, doc_type)
    for i in llm_issues:
        i.document = filename
    issues.extend(llm_issues)

    # Rule-based fallbacks — expand coverage so issues are raised even if LLM/RAG are empty
    lower = doc_text.lower()

    if doc_type == "Employment Contract":
        # Governing law must reference ADGM
        if "abu dhabi global market" not in lower and "adgm" not in lower:
            issues.append(Issue(
                document=filename,
                section=None,
                issue="Missing explicit ADGM governing law reference in employment contract.",
                severity="High",
                suggestion="Add: 'This employment contract is governed by the laws of the Abu Dhabi Global Market (ADGM).'",
            ))
        # Key terms presence checks
        checks = [
            (r"hours\s+of\s+work|working\s+hours|normal\s+working\s+hours", "Hours of work not specified.", "Include normal working hours, rest periods, and any overtime provisions."),
            (r"place\s+of\s+employment|place\s+of\s+work|work\s+location", "Place of employment not specified.", "State the usual place of employment or arrangements for remote/hybrid work."),
            (r"remuneration|salary|wage", "Remuneration/salary not specified.", "State base salary/remuneration and any allowances or bonuses."),
            (r"annual\s+leave|vacation|holiday\s+entitlement", "Annual leave entitlement not specified.", "Specify annual leave entitlement and accrual rules."),
            (r"notice\s+period|notice\s+of\s+termination|termination\s+notice", "Notice period not specified.", "Specify notice periods for termination by employer and employee."),
            (r"probation", "Probation period not specified.", "If applicable, state probation duration and conditions."),
        ]
        for pattern, msg, suggestion in checks:
            if re.search(pattern, lower) is None:
                issues.append(Issue(
                    document=filename,
                    section=None,
                    issue=msg,
                    severity="Medium",
                    suggestion=suggestion,
                ))

    if doc_type == "Articles of Association":
        # Consecutive numbering heuristic
        if not _has_sequential_numbered_paragraphs(doc):
            issues.append(Issue(
                document=filename,
                section=None,
                issue="AoA paragraphs may not be consecutively numbered.",
                severity="Medium",
                suggestion="Ensure the AoA is a single document with consecutively numbered paragraphs (Companies Regulations 2020, Art. 16).",
            ))

    # Generic jurisdiction clause check for other contracts
    if doc_type not in ("Employment Contract", "Articles of Association"):
        jurisdiction_present = ("abu dhabi global market" in lower or "adgm" in lower)
        if not jurisdiction_present:
            issues.append(Issue(
                document=filename,
                section=None,
                issue="Missing ADGM governing law / jurisdiction clause.",
                severity="High",
                suggestion="Add a clause: 'This agreement is governed by the laws of the Abu Dhabi Global Market and subject to the exclusive jurisdiction of the ADGM Courts.'",
            ))

    return issues
