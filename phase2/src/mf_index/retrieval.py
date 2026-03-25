from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from mf_index.embeddings import DEFAULT_EMBEDDING_MODEL, embed_query


def _tokens(s: str) -> set[str]:
    # Treat underscores like spaces so "expense_ratio" matches "expense ratio"
    norm = s.lower().replace("_", " ")
    return {t for t in re.split(r"[^\w]+", norm) if len(t) > 1}


def load_chunks(index_path: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    with index_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            chunks.append(json.loads(line))
    return chunks


def chunks_by_id(index_path: Path) -> dict[str, dict[str, Any]]:
    return {c["chunk_id"]: c for c in load_chunks(index_path) if c.get("chunk_id")}


def score_chunk(query: str, text: str) -> float:
    qt = _tokens(query)
    if not qt:
        return 0.0
    tt = _tokens(text)
    if not tt:
        return 0.0
    overlap = len(qt & tt)
    # light boost for exact substring of full query (normalized spaces)
    qn = re.sub(r"\s+", " ", query.strip().lower())
    bonus = 2.0 if qn and qn in text.lower() else 0.0
    return overlap + bonus


def retrieve_from_manifest(
    query: str,
    project_root: Path,
    manifest: dict[str, Any],
    *,
    top_k: int = 5,
    vector_pool: int = 24,
    lexical_weight: float = 0.12,
) -> list[tuple[dict[str, Any], float]]:
    """
    Vector search (Chroma or Pinecone) over embeddings, then light lexical re-rank on the shortlist.
    Full chunk text is loaded from chunks.jsonl by chunk_id (avoids huge Pinecone metadata).
    """
    ingest_run_id = manifest["ingest_run_id"]
    index_dir = project_root / "data" / "index" / ingest_run_id
    chunks_path = index_dir / "chunks.jsonl"
    if not chunks_path.is_file():
        return []

    model_name = manifest.get("embedding_model") or DEFAULT_EMBEDDING_MODEL
    qv = embed_query(query, model_name=model_name)
    if not qv:
        return []

    backend = manifest.get("backend")
    ranked_ids: list[tuple[str, float]] = []
    if backend == "chroma":
        from mf_index.vector_store import chroma_query

        rel = manifest.get("chroma_path")
        coll = manifest.get("chroma_collection")
        if not rel or not coll:
            return []
        chroma_path = project_root / rel
        ranked_ids = chroma_query(chroma_path, coll, qv, min(vector_pool, 256))
    elif backend == "pinecone":
        from mf_index.vector_store import pinecone_query

        idx = manifest.get("pinecone_index_name")
        ns = manifest.get("pinecone_namespace")
        if not idx or not ns:
            return []
        ranked_ids = pinecone_query(idx, ns, qv, min(vector_pool, 256))
    else:
        return []

    by_id = chunks_by_id(chunks_path)
    hits: list[tuple[dict[str, Any], float]] = []
    for chunk_id, vec_score in ranked_ids:
        c = by_id.get(chunk_id)
        if c:
            lx = score_chunk(query, c.get("text") or "")
            hits.append((c, float(vec_score) + lexical_weight * lx))

    hits.sort(key=lambda x: -x[1])
    return hits[:top_k]


def retrieve(
    query: str,
    chunks: list[dict[str, Any]],
    *,
    top_k: int = 5,
) -> list[tuple[dict[str, Any], float]]:
    scored: list[tuple[dict[str, Any], float]] = []
    for c in chunks:
        text = c.get("text") or ""
        s = score_chunk(query, text)
        if s > 0:
            scored.append((c, s))
    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]


def answer_from_chunks(query: str, hits: list[tuple[dict[str, Any], float]]) -> str:
    if not hits:
        return (
            "I couldn’t find a strong match for that in the scheme pages we’ve indexed yet. "
            "Try naming a specific fund, or ask about something like expense ratio, NAV, benchmark, exit load, or minimum SIP."
        )
    lines: list[str] = []
    for c, _score in hits:
        scheme = c.get("scheme_name") or "Fund"
        snippet = (c.get("text") or "").replace("\n", " ")
        if len(snippet) > 900:
            snippet = snippet[:897] + "..."
        lines.append(f"— {scheme}: {snippet}")
    header = (
        "Here’s what turned up from the indexed scheme pages — I’m quoting the text as stored, "
        "so you can scan for the fact you need:\n\n"
    )
    return header + "\n\n".join(lines)
