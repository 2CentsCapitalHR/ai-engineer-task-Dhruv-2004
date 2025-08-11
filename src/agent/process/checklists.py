from __future__ import annotations

from typing import Dict, List, Tuple, Set


# Checklists for key ADGM processes (prototype scope)
REQUIRED_DOCS_BY_PROCESS: Dict[str, List[str]] = {
    "Company Incorporation (Private Company)": [
        "Articles of Association",
        "Board Resolution",
        "Incorporation Application Form",
        "UBO Declaration Form",
        "Register of Members and Directors",
    ],
    "Employment Compliance": [
        "Employment Contract",
    ],
    "Data Protection Compliance": [
        "Appropriate Policy Document",
    ],
    "AoA Amendment": [
        "Articles of Association",
        "Shareholder Resolution",
    ],
}


SYNONYMS: Dict[str, Set[str]] = {
    # Composite requirement satisfied if BOTH of these are present
    "Register of Members and Directors": {"Register of Members", "Register of Directors"},
}


def compare_uploaded_to_required(process: str, uploaded_doc_types: List[str]) -> Tuple[List[str], List[str]]:
    """
    Basic comparison without composite logic. Prefer using compute_missing_docs for richer behavior.
    """
    required = REQUIRED_DOCS_BY_PROCESS.get(process, [])
    present = []
    missing = []
    for req in required:
        if req in uploaded_doc_types:
            present.append(req)
        else:
            missing.append(req)
    return present, missing


def compute_missing_docs(process: str, uploaded_doc_types: List[str]) -> Tuple[List[str], List[str]]:
    required = REQUIRED_DOCS_BY_PROCESS.get(process, [])
    uploaded_set = set(uploaded_doc_types)

    present: List[str] = []
    missing: List[str] = []

    for req in required:
        # Composite requirement
        if req in SYNONYMS:
            parts = SYNONYMS[req]
            if parts.issubset(uploaded_set):
                present.append(req)
            else:
                missing.append(req)
            continue

        # Direct match
        if req in uploaded_set:
            present.append(req)
            continue

        # Simple synonym mapping (e.g., treat Shareholder Resolution as Board Resolution if you decide to)
        if req == "Board Resolution" and "Shareholder Resolution" in uploaded_set:
            # We keep them distinct to be strict; comment next line to accept shareholder resolution instead of board
            missing.append(req)
            continue

        missing.append(req)

    return present, missing


def list_processes() -> List[str]:
    return list(REQUIRED_DOCS_BY_PROCESS.keys())
