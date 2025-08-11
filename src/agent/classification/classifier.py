from __future__ import annotations

import re
from typing import List, Optional

from docx import Document

from agent.llm.gemini_client import GeminiClient


KNOWN_LABELS: List[str] = [
    "Articles of Association",
    "Shareholder Resolution",
    "Board Resolution",
    "Incorporation Application Form",
    "Register of Members",
    "Register of Directors",
    "Employment Contract",
    "Data Protection Policy",
    "Appropriate Policy Document",
    "Other",
]


class DocumentClassifier:
    def __init__(self):
        self.gemini = GeminiClient()

    def classify(self, filename: str, doc: Document) -> str:
        # Rule-based quick checks by filename
        lower_name = filename.lower()
        if "articles" in lower_name and "association" in lower_name:
            return "Articles of Association"
        if "employment" in lower_name and "contract" in lower_name:
            return "Employment Contract"
        if "register" in lower_name and "members" in lower_name:
            return "Register of Members"
        if "register" in lower_name and "directors" in lower_name:
            return "Register of Directors"
        if "resolution" in lower_name and ("incorporation" in lower_name or "amendment" in lower_name or "articles" in lower_name):
            # Could be shareholder or board resolution
            return "Shareholder Resolution"
        if "application" in lower_name and ("incorporation" in lower_name or "registration" in lower_name):
            return "Incorporation Application Form"
        if "appropriate_policy" in lower_name:
            return "Appropriate Policy Document"
        if "data_protection" in lower_name and "policy" in lower_name:
            return "Data Protection Policy"

        # Content-based heuristics
        full_text = "\n".join(p.text for p in doc.paragraphs[:150])[:8000]
        text_lower = full_text.lower()
        if re.search(r"articles of association", text_lower):
            return "Articles of Association"
        if re.search(r"employment\s+contract|employed\s+by", text_lower):
            return "Employment Contract"
        if re.search(r"register\s+of\s+members", text_lower):
            return "Register of Members"
        if re.search(r"register\s+of\s+directors", text_lower):
            return "Register of Directors"
        if re.search(r"(shareholder|board)\s+resolution", text_lower):
            # default to Shareholder Resolution
            return "Shareholder Resolution"
        if re.search(r"application\s+for\s+(incorporation|registration)", text_lower):
            return "Incorporation Application Form"

        # Optional Gemini assist
        gemini_label: Optional[str] = self.gemini.classify(full_text, KNOWN_LABELS)
        if gemini_label:
            return gemini_label

        return "Other"
