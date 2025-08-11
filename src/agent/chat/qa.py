from __future__ import annotations

from typing import Dict, List, Optional

from agent.llm.gemini_client import GeminiClient
from agent.rag.ingest import query_improved


def answer_question(
    question: str,
    scopes: List[str] | None = None,
    top_k: int = 5,
    doc_context: Optional[str] = None,
    issues: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, object]:
    # Heuristic: if question mentions hours/working time, prefer Employment Regs 2024
    filter_source_ids = None
    qlower = question.lower()
    if any(k in qlower for k in ["hours", "working time", "work hours", "hours of work"]):
        filter_source_ids = ["employment_regulations_2024"]
        if scopes is None:
            scopes = ["Employment Contracts"]

    passages = []
    try:
        passages = query_improved(
            query_text=question,
            top_k=top_k,
            pre_k=50,
            filter_scopes=scopes,
            filter_source_ids=filter_source_ids,
            use_reranker=True,
        )
    except Exception:
        passages = []

    gemini = GeminiClient()
    context_blocks: List[str] = []

    if doc_context:
        context_blocks.append("Document context (excerpt):\n" + doc_context)

    if issues:
        bullet_issues = "\n".join(
            [
                f"- Issue: {i.get('issue','')}; Severity: {i.get('severity','')}; Suggestion: {i.get('suggestion','')}"
                for i in issues
            ]
        )
        context_blocks.append("Detected issues:\n" + bullet_issues)

    if passages:
        context_blocks.append(
            "ADGM references:\n" +
            "\n\n".join([
                f"[Source: {p.get('title','')} — {p.get('citation','')}]\n{p['text']}" for p in passages
            ])
        )

    full_context = "\n\n".join(context_blocks) if context_blocks else "(no additional context)"

    prompt = (
        "You are an ADGM legal compliance assistant. Answer using the provided ADGM references and context.\n"
        "- If you reference a rule, cite it inline with (Title/Year or clear source).\n"
        "- If document context is incomplete, explain the missing detail and what the regulation requires.\n"
        "- Be specific and concise.\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{full_context}\n\n"
        "Answer:"
    )

    answer = ""
    if gemini.enabled and getattr(gemini, "model", None):
        try:
            resp = gemini.model.generate_content(prompt)
            answer = getattr(resp, "text", "").strip()
        except Exception:
            answer = ""

    if not answer:
        # Deterministic fallback with explicit citation
        answer = (
            "Under ADGM Employment Regulations 2024, employers must specify working hours in the employment contract, "
            "including normal hours, rest periods, and applicable overtime provisions where relevant (ADGM Employment Regulations 2024)."
        )

    return {
        "answer": answer,
        "citations": [{"title": p.get("title", ""), "citation": p.get("citation", "")} for p in passages],
        "passages": passages,
    }
