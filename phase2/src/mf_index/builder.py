from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from mf_index.chunker import build_chunks_for_run, write_chunks_jsonl
from mf_index.embeddings import (
    DEFAULT_EMBEDDING_DIMENSION,
    DEFAULT_EMBEDDING_MODEL,
    embed_texts,
)
from mf_index.manifest import build_manifest, write_manifest
from mf_index.paths import project_root
from mf_index.vector_store import chroma_upsert, pinecone_upsert

Backend = Literal["chroma", "pinecone"]


def run_phase2_index(
    ingest_run_id: str,
    *,
    backend: Backend = "chroma",
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    pinecone_index_name: str | None = None,
) -> Path:
    """
    Chunk processed JSON, embed, upsert to Chroma (local) or Pinecone (cloud),
    write chunks.jsonl + index_manifest.json under data/index/<ingest_run_id>/.
    """
    root = project_root()
    proc = root / "data" / "processed" / ingest_run_id
    if not proc.is_dir():
        raise FileNotFoundError(f"Processed run not found: {proc}")

    chunks = build_chunks_for_run(proc)
    index_dir = root / "data" / "index" / ingest_run_id
    jsonl_rel = f"data/index/{ingest_run_id}/chunks.jsonl"
    write_chunks_jsonl(chunks, index_dir / "chunks.jsonl")

    texts = [c.get("text") or "" for c in chunks]
    embeddings = embed_texts(texts, model_name=embedding_model)

    dim = len(embeddings[0]) if embeddings else DEFAULT_EMBEDDING_DIMENSION

    if backend == "chroma":
        chroma_dir = index_dir / "chroma_db"
        coll_name = chroma_upsert(chroma_dir, ingest_run_id, chunks, embeddings)
        manifest = build_manifest(
            ingest_run_id=ingest_run_id,
            backend="chroma",
            embedding_model=embedding_model,
            embedding_dimension=dim,
            chunks_jsonl_relative=jsonl_rel,
            chroma_relative_path=f"data/index/{ingest_run_id}/chroma_db",
            chroma_collection=coll_name,
        )
    elif backend == "pinecone":
        idx_name = pinecone_index_name or os.environ.get("PINECONE_INDEX", "mf-rag")
        pinecone_upsert(idx_name, ingest_run_id, chunks, embeddings)
        manifest = build_manifest(
            ingest_run_id=ingest_run_id,
            backend="pinecone",
            embedding_model=embedding_model,
            embedding_dimension=dim,
            chunks_jsonl_relative=jsonl_rel,
            pinecone_index_name=idx_name,
            pinecone_namespace=ingest_run_id,
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")

    write_manifest(index_dir, manifest)
    return index_dir
