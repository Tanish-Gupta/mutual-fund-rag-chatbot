from __future__ import annotations

import hashlib
import json
from pathlib import Path


def project_root() -> Path:
    here = Path(__file__).resolve()
    for d in [here, *here.parents]:
        if (d / "pyproject.toml").is_file():
            return d
    raise RuntimeError("Cannot locate project root (pyproject.toml)")


def data_dir() -> Path:
    return project_root() / "data"


def raw_run_dir(ingest_run_id: str) -> Path:
    return data_dir() / "raw" / ingest_run_id


def manifests_dir() -> Path:
    d = data_dir() / "manifests"
    d.mkdir(parents=True, exist_ok=True)
    return d


def processed_run_dir(ingest_run_id: str) -> Path:
    return data_dir() / "processed" / ingest_run_id


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")
