from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

BackendName = Literal["chroma", "pinecone"]


def manifest_path(index_dir: Path) -> Path:
    return index_dir / "index_manifest.json"


def write_manifest(index_dir: Path, data: dict[str, Any]) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    manifest_path(index_dir).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_manifest(index_dir: Path) -> dict[str, Any] | None:
    p = manifest_path(index_dir)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def build_manifest(
    *,
    ingest_run_id: str,
    backend: BackendName,
    embedding_model: str,
    embedding_dimension: int,
    chunks_jsonl_relative: str,
    chroma_relative_path: str | None = None,
    chroma_collection: str | None = None,
    pinecone_index_name: str | None = None,
    pinecone_namespace: str | None = None,
) -> dict[str, Any]:
    m: dict[str, Any] = {
        "ingest_run_id": ingest_run_id,
        "backend": backend,
        "embedding_model": embedding_model,
        "embedding_dimension": embedding_dimension,
        "chunks_jsonl": chunks_jsonl_relative,
        "phase": "process_index",
    }
    if backend == "chroma":
        m["chroma_path"] = chroma_relative_path
        m["chroma_collection"] = chroma_collection
    elif backend == "pinecone":
        m["pinecone_index_name"] = pinecone_index_name
        m["pinecone_namespace"] = pinecone_namespace
    return m
