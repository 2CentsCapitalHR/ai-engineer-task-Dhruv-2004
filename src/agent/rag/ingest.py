from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from agent.knowledge.manifest import SourcesManifest, SourceEntry

# Parsers
try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None  # type: ignore

try:
    import pypdf  # type: ignore
except Exception:
    pypdf = None  # type: ignore

try:
    import docx  # type: ignore
except Exception:
    docx = None  # type: ignore

# Embeddings & Vector store
try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:
    SentenceTransformer = None  # type: ignore

try:
    import chromadb  # type: ignore
    from chromadb.utils import embedding_functions  # type: ignore
except Exception:
    chromadb = None  # type: ignore
    embedding_functions = None  # type: ignore

# Optional reranker
try:
    from sentence_transformers import CrossEncoder  # type: ignore
except Exception:
    CrossEncoder = None  # type: ignore


@dataclass
class IngestConfig:
    collection_name: str = "adgm_sources"
    chunk_size: int = 800
    chunk_overlap: int = 150
    embedding_model: str = "sentence-transformers/all-mpnet-base-v2"


def _resolve_source_path(root_dir: str, rel_path: str) -> Optional[str]:
    candidates = [
        os.path.join(root_dir, rel_path),
        os.path.join(root_dir, "data", rel_path),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _read_text(abs_path: str) -> str:
    _, ext = os.path.splitext(abs_path)
    ext = ext.lower()

    if ext in [".html", ".htm"] and BeautifulSoup:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator="\n")

    if ext in [".pdf"] and pypdf:
        text = []
        with open(abs_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text.append(page.extract_text() or "")
        return "\n".join(text)

    if ext in [".docx"] and docx:
        d = docx.Document(abs_path)
        return "\n".join(p.text for p in d.paragraphs)

    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def read_text_from_source(root_dir: str, source: SourceEntry) -> str:
    abs_path = _resolve_source_path(root_dir, source.path)
    if not abs_path:
        return ""
    return _read_text(abs_path)


def chunk_text(text: str, size: int, overlap: int) -> List[str]:
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunk = text[start:end]
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def get_or_create_collection(client, name: str, embedding_func):
    try:
        return client.get_collection(name)
    except Exception:
        return client.create_collection(name=name, embedding_function=embedding_func)


def ingest_sources(root_dir: str, config: Optional[IngestConfig] = None) -> Dict[str, int]:
    assert chromadb is not None, "chromadb not installed"
    assert SentenceTransformer is not None, "sentence-transformers not installed"

    cfg = config or IngestConfig()

    manifest = SourcesManifest.load(os.path.join(root_dir, "data", "sources_manifest.json"))

    client = chromadb.Client()
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=cfg.embedding_model)
    collection = get_or_create_collection(client, cfg.collection_name, embedding_func)

    total_chunks = 0

    for src in manifest.all():
        text = read_text_from_source(root_dir, src)
        if not text or not text.strip():
            continue
        chunks = chunk_text(text, cfg.chunk_size, cfg.chunk_overlap)
        if not chunks:
            continue
        ids = [f"{src.id}_{i}" for i in range(len(chunks))]
        scope_str = ";".join(src.scope) if src.scope else ""
        metadatas = [{
            "source_id": src.id,
            "title": src.title,
            "type": src.type,
            "citation": src.citation,
            "scope": scope_str,
        } for _ in chunks]
        collection.add(ids=ids, documents=chunks, metadatas=metadatas)
        total_chunks += len(chunks)

    return {"chunks_indexed": total_chunks}


def inspect_sources(root_dir: str) -> List[Dict[str, str]]:
    manifest = SourcesManifest.load(os.path.join(root_dir, "data", "sources_manifest.json"))
    out: List[Dict[str, str]] = []
    for src in manifest.all():
        resolved = _resolve_source_path(root_dir, src.path)
        exists = bool(resolved and os.path.exists(resolved))
        length = 0
        ext = ""
        if resolved and exists:
            ext = os.path.splitext(resolved)[1].lower()
            text = _read_text(resolved)
            length = len(text or "")
        out.append({
            "id": src.id,
            "path": src.path,
            "resolved": resolved or "(not found)",
            "exists": str(exists),
            "ext": ext,
            "text_length": str(length),
        })
    return out


def query(top_k: int, query_text: str, collection_name: str = "adgm_sources") -> List[Dict[str, str]]:
    assert chromadb is not None, "chromadb not installed"
    client = chromadb.Client()
    collection = client.get_collection(collection_name)
    result = collection.query(query_texts=[query_text], n_results=top_k)
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    out: List[Dict[str, str]] = []
    for d, m in zip(docs, metas):
        out.append({"text": d, **{k: str(v) for k, v in (m or {}).items()}})
    return out


def query_improved(
    query_text: str,
    top_k: int = 5,
    pre_k: int = 30,
    collection_name: str = "adgm_sources",
    filter_scopes: Optional[List[str]] = None,
    filter_source_ids: Optional[List[str]] = None,
    use_reranker: bool = True,
) -> List[Dict[str, str]]:
    assert chromadb is not None, "chromadb not installed"
    client = chromadb.Client()
    collection = client.get_collection(collection_name)

    pre = collection.query(query_texts=[query_text], n_results=max(pre_k, top_k))
    docs = pre.get("documents", [[]])[0]
    metas = pre.get("metadatas", [[]])[0]

    candidates: List[Tuple[str, Dict[str, str]]] = []
    for d, m in zip(docs, metas):
        md = {k: str(v) for k, v in (m or {}).items()}
        candidates.append((d, md))

    if filter_scopes:
        scope_lower = [s.lower() for s in filter_scopes]
        filtered = [
            (d, m) for (d, m) in candidates
            if any(s in m.get("scope", "").lower() for s in scope_lower)
        ]
        if filtered:
            candidates = filtered

    if filter_source_ids:
        filtered = [(d, m) for (d, m) in candidates if m.get("source_id") in set(filter_source_ids)]
        if filtered:
            candidates = filtered

    if use_reranker and CrossEncoder is not None and candidates:
        try:
            reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            pairs = [(query_text, d) for (d, _) in candidates]
            scores = reranker.predict(pairs)
            ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
            candidates = [c for (c, s) in ranked]
        except Exception:
            pass

    trimmed = candidates[:top_k]
    return [{"text": d, **m} for (d, m) in trimmed]
