from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    here = Path(__file__).resolve()
    for d in [here, *here.parents]:
        if (d / "pyproject.toml").is_file():
            return d
    raise RuntimeError("Cannot locate project root (pyproject.toml)")


def index_run_dir(ingest_run_id: str) -> Path:
    return project_root() / "data" / "index" / ingest_run_id
