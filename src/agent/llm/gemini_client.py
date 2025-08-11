from __future__ import annotations

from typing import List, Optional

from agent.config import CONFIG

try:
    import google.generativeai as genai  # type: ignore
    _HAS_GEMINI = True
except Exception:
    _HAS_GEMINI = False


class GeminiClient:
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        self.enabled = _HAS_GEMINI and bool(CONFIG.gemini_api_key) and CONFIG.llm_provider.lower() == "gemini"
        if self.enabled:
            genai.configure(api_key=CONFIG.gemini_api_key)
            self.model = genai.GenerativeModel(model_name)
        else:
            self.model = None

    def classify(self, text: str, labels: List[str]) -> Optional[str]:
        if not self.enabled or not self.model:
            return None
        prompt = (
            "You are a legal document classifier for ADGM corporate workflows.\n"
            f"Choose only one of these labels: {labels}.\n"
            "Given the document content below, return only the best label without explanation.\n"
            "Document:\n" + text[:4000]
        )
        try:
            resp = self.model.generate_content(prompt)
            if hasattr(resp, "text") and resp.text:
                candidate = resp.text.strip()
                # Normalize to one of the labels if possible
                for label in labels:
                    if label.lower() in candidate.lower():
                        return label
                # Fallback: exact match or first token
                if candidate in labels:
                    return candidate
                return None
        except Exception:
            return None
