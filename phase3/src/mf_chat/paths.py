from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def project_root() -> Path:
    here = Path(__file__).resolve()
    for d in [here, *here.parents]:
        if (d / "pyproject.toml").is_file():
            return d
    raise RuntimeError("Cannot locate project root (pyproject.toml)")


def latest_index_run_id() -> str | None:
    root = project_root()
    idx_root = root / "data" / "index"
    if not idx_root.is_dir():
        return None
    candidates: list[tuple[float, str]] = []
    for d in idx_root.iterdir():
        if not d.is_dir():
            continue
        mf = d / "index_manifest.json"
        ch = d / "chunks.jsonl"
        if mf.is_file():
            candidates.append((mf.stat().st_mtime, d.name))
        elif ch.is_file():
            candidates.append((ch.stat().st_mtime - 1e9, d.name))
    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]


def latest_index_last_modified_utc() -> tuple[str | None, str | None]:
    """
    Latest index run id and last modification time of its manifest (or chunks.jsonl) as ISO-8601 UTC string.
    """
    rid = latest_index_run_id()
    if not rid:
        return None, None
    root = project_root()
    idx_dir = root / "data" / "index" / rid
    for fname in ("index_manifest.json", "chunks.jsonl"):
        p = idx_dir / fname
        if p.is_file():
            ts = p.stat().st_mtime
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            iso = dt.isoformat().replace("+00:00", "Z")
            return rid, iso
    return rid, None
