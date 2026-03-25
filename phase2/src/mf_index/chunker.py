from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any


def _norm_key(k: str) -> str:
    return re.sub(r"[_\s]+", " ", k.strip().lower())


def _snapshot_lines(snapshot: dict[str, Any]) -> str:
    lines: list[str] = []
    for key in sorted(snapshot.keys()):
        val = snapshot.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            continue
        lines.append(f"{key}: {val}")
    return "\n".join(lines)


def _flatten_performance(perf: dict[str, Any] | None) -> str:
    if not perf or not isinstance(perf, dict):
        return ""
    parts: list[str] = []
    for k, v in perf.items():
        if isinstance(v, (list, dict)):
            parts.append(f"{k}: {json.dumps(v, default=str)[:2000]}")
        elif v is not None:
            parts.append(f"{k}: {v}")
    return "\n".join(parts)


def _scheme_id_from_doc(doc: dict[str, Any]) -> int | None:
    nd = doc.get("next_data_snippet")
    if not isinstance(nd, dict):
        return None
    sid = nd.get("schemeId")
    if isinstance(sid, int):
        return sid
    if isinstance(sid, str) and sid.isdigit():
        return int(sid)
    return None


def chunks_from_processed_doc(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn one processed JSON record into searchable chunks; each chunk carries canonical_url + metadata for Phase 2."""
    source_url = doc.get("source_url") or ""
    scheme_name = doc.get("scheme_name") or ""
    scheme_id = _scheme_id_from_doc(doc)
    out: list[dict[str, Any]] = []

    def base_meta() -> dict[str, Any]:
        return {
            "canonical_url": source_url,
            "doc_type": "indmoney_scheme",
            **({"scheme_id": scheme_id} if scheme_id is not None else {}),
        }

    snap = doc.get("snapshot") or {}
    if isinstance(snap, dict) and snap:
        text = _snapshot_lines(snap)
        if text.strip():
            out.append(
                {
                    "chunk_id": str(uuid.uuid4()),
                    "source_url": source_url,
                    "scheme_name": scheme_name,
                    "kind": "snapshot",
                    "text": f"Scheme: {scheme_name}\n{text}".strip(),
                    **base_meta(),
                }
            )

    sections = doc.get("sections") or {}
    if isinstance(sections, dict):
        for title, body in sections.items():
            if not isinstance(body, str) or not body.strip():
                continue
            out.append(
                {
                    "chunk_id": str(uuid.uuid4()),
                    "source_url": source_url,
                    "scheme_name": scheme_name,
                    "kind": f"section:{_norm_key(str(title))}",
                    "text": f"Scheme: {scheme_name}\n{title}\n{body}".strip(),
                    **base_meta(),
                }
            )

    perf = doc.get("performance_table")
    flat = _flatten_performance(perf if isinstance(perf, dict) else None)
    if flat.strip():
        out.append(
            {
                "chunk_id": str(uuid.uuid4()),
                "source_url": source_url,
                "scheme_name": scheme_name,
                "kind": "performance",
                "text": f"Scheme: {scheme_name}\nPerformance\n{flat}".strip(),
                **base_meta(),
            }
        )

    managers = doc.get("fund_managers") or []
    if isinstance(managers, list) and managers:
        lines = [f"Scheme: {scheme_name}", "Fund managers"]
        for m in managers:
            if isinstance(m, dict):
                lines.append(json.dumps(m, ensure_ascii=False))
        out.append(
            {
                "chunk_id": str(uuid.uuid4()),
                "source_url": source_url,
                "scheme_name": scheme_name,
                "kind": "fund_managers",
                "text": "\n".join(lines),
                **base_meta(),
            }
        )

    return out


def build_chunks_for_run(processed_dir: Path) -> list[dict[str, Any]]:
    if not processed_dir.is_dir():
        raise FileNotFoundError(f"No processed directory: {processed_dir}")
    all_chunks: list[dict[str, Any]] = []
    for path in sorted(processed_dir.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            continue
        all_chunks.extend(chunks_from_processed_doc(doc))
    return all_chunks


def write_chunks_jsonl(chunks: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
