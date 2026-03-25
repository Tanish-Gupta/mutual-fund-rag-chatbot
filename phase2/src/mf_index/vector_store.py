from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _chroma_meta(chunk: dict[str, Any], ingest_run_id: str) -> dict[str, Any]:
    sid = chunk.get("scheme_id")
    return {
        "source_url": (chunk.get("source_url") or "")[:2000],
        "scheme_name": (chunk.get("scheme_name") or "")[:1000],
        "kind": (chunk.get("kind") or "")[:500],
        "scheme_id": str(sid) if sid is not None else "",
        "ingest_run_id": ingest_run_id,
    }


def chroma_collection_name(ingest_run_id: str) -> str:
    return f"mf_rag_{ingest_run_id.replace('-', '_')}"


def chroma_upsert(
    persist_dir: Path,
    ingest_run_id: str,
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
) -> str:
    try:
        import chromadb
    except ImportError as e:
        raise ImportError("Install Chroma: pip install -e '.[vector]'") from e

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    name = chroma_collection_name(ingest_run_id)
    try:
        client.delete_collection(name)
    except Exception:
        pass
    coll = client.create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
    coll.add(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=embeddings,
        documents=[c.get("text") or "" for c in chunks],
        metadatas=[_chroma_meta(c, ingest_run_id) for c in chunks],
    )
    return name


def chroma_query(
    persist_dir: Path,
    collection_name: str,
    query_embedding: list[float],
    top_k: int,
) -> list[tuple[str, float]]:
    import chromadb

    client = chromadb.PersistentClient(path=str(persist_dir))
    coll = client.get_collection(name=collection_name)
    res = coll.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["distances"],
    )
    ids = (res.get("ids") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    # Cosine space: distance is often (1 - cosine similarity); lower is better
    out: list[tuple[str, float]] = []
    for cid, d in zip(ids, dists):
        sim = 1.0 - float(d) if d is not None else 0.0
        out.append((cid, max(0.0, sim)))
    return out


def _pinecone_meta(chunk: dict[str, Any]) -> dict[str, Any]:
    sid = chunk.get("scheme_id")
    return {
        "source_url": (chunk.get("source_url") or "")[:1000],
        "scheme_name": (chunk.get("scheme_name") or "")[:500],
        "kind": (chunk.get("kind") or "")[:200],
        "scheme_id": str(sid) if sid is not None else "",
    }


def pinecone_upsert(
    index_name: str,
    namespace: str,
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
) -> None:
    try:
        from pinecone import Pinecone
    except ImportError as e:
        raise ImportError("Install Pinecone: pip install -e '.[vector]'") from e

    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        raise RuntimeError("PINECONE_API_KEY is required for Pinecone backend")

    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)
    batch: list[dict[str, Any]] = []
    for c, emb in zip(chunks, embeddings):
        batch.append(
            {
                "id": c["chunk_id"],
                "values": emb,
                "metadata": _pinecone_meta(c),
            }
        )
    for i in range(0, len(batch), 100):
        index.upsert(vectors=batch[i : i + 100], namespace=namespace)


def pinecone_query(
    index_name: str,
    namespace: str,
    query_embedding: list[float],
    top_k: int,
) -> list[tuple[str, float]]:
    from pinecone import Pinecone

    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        raise RuntimeError("PINECONE_API_KEY is required for Pinecone backend")

    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)
    res = index.query(
        namespace=namespace,
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
    )
    out: list[tuple[str, float]] = []
    matches = getattr(res, "matches", None)
    if matches is None and isinstance(res, dict):
        matches = res.get("matches") or []
    if matches is None:
        matches = []
    for m in matches:
        mid = getattr(m, "id", None)
        score = getattr(m, "score", None)
        if isinstance(m, dict):
            mid = mid or m.get("id")
            if score is None:
                score = m.get("score", 0.0)
        if mid:
            out.append((str(mid), float(score if score is not None else 0.0)))
    return out
