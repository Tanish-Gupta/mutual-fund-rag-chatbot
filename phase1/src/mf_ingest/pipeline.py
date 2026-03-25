from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from mf_ingest.config import assert_allowlisted_url, slug_from_url
from mf_ingest.fetcher import fetch_url_http, fetch_url_playwright
from mf_ingest.indmoney_parser import parse_indmoney_html
from mf_ingest.models import FetchOutcome, IngestManifest, SourceRecord
from mf_ingest.storage import (
    manifests_dir,
    processed_run_dir,
    raw_run_dir,
    sha256_bytes,
    write_bytes,
    write_json,
)


def run_ingest(
    urls: list[str],
    *,
    trigger: str = "manual",
    use_browser: bool = False,
    parse_structured: bool = True,
    ingest_run_id: str | None = None,
) -> IngestManifest:
    rid = ingest_run_id or str(uuid.uuid4())
    started = datetime.now(timezone.utc)
    manifest = IngestManifest(ingest_run_id=rid, trigger=trigger, started_at=started)
    raw_dir = raw_run_dir(rid)
    proc_dir = processed_run_dir(rid) if parse_structured else None

    errors = 0
    for url in urls:
        assert_allowlisted_url(url)
        slug = slug_from_url(url)
        try:
            if use_browser:
                fr = fetch_url_playwright(url)
            else:
                fr = fetch_url_http(url)
        except RuntimeError as e:
            manifest.sources.append(
                SourceRecord(
                    source_url=url,
                    slug=slug,
                    outcome=FetchOutcome.ERROR,
                    error_message=str(e),
                )
            )
            errors += 1
            continue

        h = sha256_bytes(fr.body)
        rel_path = f"data/raw/{rid}/{slug}.html"
        out_path = raw_dir / f"{slug}.html"
        write_bytes(out_path, fr.body)

        notes = None
        if fr.outcome == FetchOutcome.CLOUDFLARE_CHALLENGE:
            notes = fr.error_message

        manifest.sources.append(
            SourceRecord(
                source_url=url,
                slug=slug,
                outcome=fr.outcome,
                http_status=fr.status_code,
                content_hash=h,
                raw_relative_path=rel_path,
                byte_size=len(fr.body),
                error_message=fr.error_message if fr.outcome != FetchOutcome.FETCHED else None,
                notes=notes,
            )
        )

        if fr.outcome != FetchOutcome.FETCHED:
            errors += 1
            continue

        if parse_structured and proc_dir is not None:
            html = fr.body.decode("utf-8", errors="replace")
            structured = parse_indmoney_html(html, url)
            write_json(proc_dir / f"{slug}.json", structured.model_dump())

    manifest.finished_at = datetime.now(timezone.utc)
    manifest.status = "success" if errors == 0 else ("partial" if errors < len(urls) else "failed")
    write_json(manifests_dir() / f"{rid}.json", manifest.model_dump())
    return manifest


def ingest_local_html(path: Path, source_url: str, *, parse_structured: bool = True) -> IngestManifest:
    """Import a browser-saved HTML file (bypasses fetch)."""
    assert_allowlisted_url(source_url)
    rid = str(uuid.uuid4())
    slug = slug_from_url(source_url)
    raw_dir = raw_run_dir(rid)
    proc_dir = processed_run_dir(rid) if parse_structured else None

    body = path.read_bytes()
    h = sha256_bytes(body)
    write_bytes(raw_dir / f"{slug}.html", body)

    manifest = IngestManifest(
        ingest_run_id=rid,
        trigger="import_html",
        started_at=datetime.now(timezone.utc),
        sources=[
            SourceRecord(
                source_url=source_url,
                slug=slug,
                outcome=FetchOutcome.FETCHED,
                http_status=None,
                content_hash=h,
                raw_relative_path=f"data/raw/{rid}/{slug}.html",
                byte_size=len(body),
                notes="Imported from local file",
            )
        ],
    )

    if parse_structured and proc_dir is not None:
        html = body.decode("utf-8", errors="replace")
        structured = parse_indmoney_html(html, source_url)
        write_json(proc_dir / f"{slug}.json", structured.model_dump())

    manifest.finished_at = datetime.now(timezone.utc)
    manifest.status = "success"
    write_json(manifests_dir() / f"{rid}.json", manifest.model_dump())
    return manifest
