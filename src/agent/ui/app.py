from __future__ import annotations

# Ensure 'src' is on sys.path when running via `streamlit run src/agent/ui/app.py`
import os
import sys
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import io
import importlib
from typing import List, Tuple, Dict, Any
from zipfile import ZipFile, ZIP_DEFLATED

import streamlit as st
from docx import Document

from agent.config import CONFIG
from agent.doc_processing.parser import (
    load_document_from_bytes,
    parse_document_structure,
    summarize_structure,
)
from agent.doc_processing.annotator import add_issue_comments
from agent.reporting.report import BatchReport, FileReport, Issue
from agent.classification.classifier import DocumentClassifier
from agent.process.inference import infer_process
from agent.process.checklists import REQUIRED_DOCS_BY_PROCESS, compare_uploaded_to_required
from agent.rag.ingest import ingest_sources, query as rag_query
from agent.analysis.checks import analyze_document
from agent.chat.qa import answer_question


st.set_page_config(page_title="ADGM Corporate Agent", page_icon="⚖️", layout="centered")

st.title("ADGM Corporate Agent")

st.caption("Upload .docx files, run analysis, and download reviewed docs with a JSON report.")


def _compute_missing(process: str, detected_types: List[str]) -> Tuple[List[str], List[str]]:
    try:
        import agent.process.checklists as cl
        importlib.reload(cl)
        if hasattr(cl, "compute_missing_docs"):
            return cl.compute_missing_docs(process, detected_types)  # type: ignore[attr-defined]
    except Exception:
        pass
    # Fallback
    return compare_uploaded_to_required(process, detected_types)


def run_analysis(uploaded_files: List[Any], include_comments: bool, forced_process: str | None) -> Dict[str, Any]:
    files_reports: List[FileReport] = []
    packaged_files: List[Tuple[str, bytes]] = []
    classifier = DocumentClassifier()
    detected_types: List[str] = []
    doc_text_map: Dict[str, str] = {}

    for f in uploaded_files or []:
        data = f.getvalue()
        doc = load_document_from_bytes(data)

        blocks = parse_document_structure(doc)
        summary = summarize_structure(blocks)

        doc_type = classifier.classify(f.name, doc)
        detected_types.append(doc_type)

        # Keep a short excerpt for Q&A context
        excerpt = "\n".join(p.text for p in doc.paragraphs)[:4000]
        doc_text_map[f.name] = excerpt

        rag_issues = analyze_document(doc, f.name, doc_type)

        reviewed_doc = doc
        if include_comments and rag_issues:
            reviewed_doc = add_issue_comments(
                document=doc,
                issues=[i.model_dump() for i in rag_issues],
                author=CONFIG.comment_author,
                initials=CONFIG.comment_initials,
            )

        reviewed_buffer = io.BytesIO()
        reviewed_doc.save(reviewed_buffer)
        reviewed_bytes = reviewed_buffer.getvalue()

        files_reports.append(
            FileReport(
                filename=f.name,
                document_type=doc_type,
                structure_summary=summary,
                issues_found=rag_issues,
            )
        )
        packaged_files.append((f"reviewed_{f.name}", reviewed_bytes))

    auto_process = infer_process(detected_types)
    process = forced_process or auto_process

    # Use lazy import compute_missing_docs with fallback
    present, missing = _compute_missing(process, detected_types)

    if missing and files_reports:
        for m in missing:
            files_reports[0].issues_found.append(
                Issue(
                    document=files_reports[0].filename,
                    section=None,
                    issue=f"Missing required document for process '{process}': {m}",
                    severity="High",
                    suggestion="Please upload this document to satisfy the ADGM checklist.",
                )
            )

    batch = BatchReport(
        process=process,
        documents_uploaded=len(files_reports),
        required_documents=len(REQUIRED_DOCS_BY_PROCESS.get(process, [])),
        missing_documents=missing,
        files=files_reports,
    )

    return {
        "files_reports": files_reports,
        "packaged_files": packaged_files,
        "batch": batch,
        "detected_types": detected_types,
        "auto_process": auto_process,
        "process": process,
        "doc_text_map": doc_text_map,
    }


uploaded_files = st.file_uploader(
    "Upload .docx files",
    type=["docx"],
    accept_multiple_files=True,
    help="Only .docx files are supported.",
    key="uploader",
)

include_comments = st.checkbox("Insert inline comments", value=True, key="include_comments")

# Build process options locally to avoid hot-reload import issues
_process_options = ["(auto)"] + sorted(list(REQUIRED_DOCS_BY_PROCESS.keys()))
manual_process = st.selectbox("Intended process (optional)", options=_process_options)
forced_process = None if manual_process == "(auto)" else manual_process

if uploaded_files:
    st.write(f"Files uploaded: {len(uploaded_files)}")

if st.button("Run Analysis", type="primary", disabled=not uploaded_files, key="run_btn"):
    st.session_state["last_run"] = run_analysis(uploaded_files, include_comments, forced_process)

# Always render results if present
run = st.session_state.get("last_run")
if run:
    files_reports: List[FileReport] = run["files_reports"]
    packaged_files: List[Tuple[str, bytes]] = run["packaged_files"]
    batch: BatchReport = run["batch"]
    doc_text_map: Dict[str, str] = run["doc_text_map"]
    auto_process: str = run["auto_process"]

    # Compact per-file previews
    for fr, (fname, fb) in zip(files_reports, packaged_files):
        with st.expander(fr.filename, expanded=False):
            counts = fr.structure_summary
            st.write(f"Type: {fr.document_type} · Headings: {counts.get('num_headings', 0)} · Paragraphs: {counts.get('num_paragraphs', 0)}")
            if fr.issues_found:
                st.write("Issues:")
                for it in fr.issues_found:
                    st.write(f"- [{it.severity}] {it.issue}")
            else:
                st.write("No issues detected.")
            st.download_button(
                label="Download Reviewed .docx",
                data=fb,
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    # Compact process & checklist
    st.write(f"Process: {batch.process}" + (" (auto: " + auto_process + ")" if batch.process != auto_process else ""))
    required_list = REQUIRED_DOCS_BY_PROCESS.get(batch.process, [])
    if not required_list:
        st.info("No checklist configured for this process.")
    elif batch.missing_documents:
        st.error(f"Missing {len(batch.missing_documents)} required document(s):")
        for m in batch.missing_documents:
            st.markdown(f"- `{m}`")
    else:
        st.success("All required documents detected for this process.")

    # Downloads
    report_json = batch.to_json(indent=2)
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download JSON Report",
            data=report_json.encode("utf-8"),
            file_name="adgm_report.json",
            mime="application/json",
            use_container_width=True,
        )
    with col2:
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, mode="w", compression=ZIP_DEFLATED) as zf:
            zf.writestr("adgm_report.json", report_json)
            for fname, fb in packaged_files:
                zf.writestr(fname, fb)
        st.download_button(
            label="Download All (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="adgm_reviewed_docs_and_report.zip",
            mime="application/zip",
            use_container_width=True,
        )

    with st.expander("Q&A (optional)"):
        doc_names = [fr.filename for fr in files_reports]
        target_doc = st.selectbox("Context document", options=["(none)"] + doc_names)
        context_text = doc_text_map.get(target_doc) if target_doc != "(none)" else None
        context_issues = None
        if target_doc != "(none)":
            for fr in files_reports:
                if fr.filename == target_doc:
                    context_issues = [i.model_dump() for i in fr.issues_found]
                    break
        question = st.text_input("Ask a question", value="Why was the jurisdiction clause flagged?", key="qa_question")
        scopes = st.multiselect("Scopes", ["AoA", "Employment Contracts", "Company Incorporation", "Jurisdiction/Choice-of-Law", "Data Protection", "Privacy"], key="qa_scopes")
        if st.button("Ask", key="qa_ask"):
            try:
                import agent.chat.qa as qa_mod
                importlib.reload(qa_mod)
                resp = qa_mod.answer_question(question, scopes=scopes or None, top_k=5, doc_context=context_text, issues=context_issues)
            except TypeError:
                resp = answer_question(question, scopes=scopes or None, top_k=5)
            st.markdown(resp.get("answer") or "")
            if resp.get("citations"):
                st.caption("Citations")
                st.json(resp.get("citations"))

with st.sidebar:
    st.header("Settings")
    st.text(f"ENV: {CONFIG.app_env}")
    st.text(f"LLM: {CONFIG.llm_provider}")

    with st.expander("Advanced (RAG tools)"):
        if st.button("Build/Refresh Index"):
            try:
                root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
                from agent.rag.ingest import ingest_sources as _ingest
                stats = _ingest(root)
                st.success(f"Indexed chunks: {stats['chunks_indexed']}")
            except AssertionError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Ingestion error: {e}")
        if st.button("Inspect Sources"):
            try:
                root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
                from agent.rag.ingest import inspect_sources as _inspect
                report = _inspect(root)
                st.json(report)
            except Exception as e:
                st.error(f"Inspect error: {e}")
        query_text = st.text_input("Quick search", value="Articles of Association numbering requirements", key="basic_query")
        if st.button("Search", key="basic_search"):
            try:
                results = rag_query(top_k=5, query_text=query_text)
                st.write(results)
            except Exception as e:
                st.error(f"Query error: {e}")
