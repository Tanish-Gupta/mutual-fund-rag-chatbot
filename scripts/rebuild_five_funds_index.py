#!/usr/bin/env python3
"""
Merge four already-fetched scheme pages with a fresh Playwright fetch for Flexi Cap,
then run Phase 2 (Chroma) for a new ingest_run_id.

Usage (from repo root, with PYTHONPATH set as in README):

  export PYTHONPATH="phase1/src:phase2/src:phase3/src:phase5/src"
  .venv/bin/python scripts/rebuild_five_funds_index.py
"""
from __future__ import annotations

import argparse
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Repo root = parent of scripts/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "phase1" / "src"))
sys.path.insert(0, str(ROOT / "phase2" / "src"))

from mf_ingest.config import DEFAULT_SEED_URLS, assert_allowlisted_url, slug_from_url  # noqa: E402
from mf_ingest.fetcher import fetch_url_http, fetch_url_playwright  # noqa: E402
from mf_ingest.indmoney_parser import parse_indmoney_html  # noqa: E402
from mf_ingest.models import FetchOutcome, IngestManifest, SourceRecord  # noqa: E402
from mf_ingest.storage import (  # noqa: E402
    manifests_dir,
    processed_run_dir,
    raw_run_dir,
    sha256_bytes,
    write_bytes,
    write_json,
)
from mf_index.builder import run_phase2_index  # noqa: E402
from mf_index.paths import project_root  # noqa: E402

BASE_SLUGS = (
    "edelweiss-emerging-markets-opportunities-equity-offshore-direct-growth-5466",
    "edelweiss-europe-dynamic-equity-offshore-fund-direct-growth-5468",
    "edelweiss-greater-china-equity-off-shore-fund-direct-plan-growth-5470",
    "edelweiss-us-technology-equity-fund-of-fund-direct-growth-1005498",
)
FLEXI_URL = "https://www.indmoney.com/mutual-funds/edelweiss-flexi-cap-fund-direct-growth-3174"

URL_BY_SLUG: dict[str, str] = {slug_from_url(u): u for u in DEFAULT_SEED_URLS}


def _find_base_processed_dir() -> Path | None:
    proc_root = project_root() / "data" / "processed"
    if not proc_root.is_dir():
        return None
    candidates: list[tuple[float, Path]] = []
    for d in proc_root.iterdir():
        if not d.is_dir():
            continue
        if all((d / f"{slug}.json").is_file() for slug in BASE_SLUGS):
            ts = max((d / f"{slug}.json").stat().st_mtime for slug in BASE_SLUGS)
            candidates.append((ts, d))
    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--base-run",
        help="processed/<id> to copy the four non–Flexi Cap JSON/HTML from (default: auto-detect)",
    )
    p.add_argument("--backend", choices=("chroma", "pinecone"), default="chroma")
    args = p.parse_args()

    if args.base_run:
        base_proc = project_root() / "data" / "processed" / args.base_run
        base_raw = project_root() / "data" / "raw" / args.base_run
    else:
        base_proc = _find_base_processed_dir()
        if base_proc is None:
            print("No existing processed run with all four base schemes. Run mf-ingest once first.", file=sys.stderr)
            sys.exit(1)
        base_raw = project_root() / "data" / "raw" / base_proc.name

    rid = str(uuid.uuid4())
    raw_dst = raw_run_dir(rid)
    proc_dst = processed_run_dir(rid)
    raw_dst.mkdir(parents=True)
    proc_dst.mkdir(parents=True)

    manifest = IngestManifest(ingest_run_id=rid, trigger="merge_four_plus_flexi_playwright")

    for slug in BASE_SLUGS:
        src_html = base_raw / f"{slug}.html"
        src_json = base_proc / f"{slug}.json"
        if not src_html.is_file() or not src_json.is_file():
            print(f"Missing {slug} under {base_raw.name}", file=sys.stderr)
            sys.exit(1)
        shutil.copy2(src_html, raw_dst / f"{slug}.html")
        shutil.copy2(src_json, proc_dst / f"{slug}.json")
        body = (raw_dst / f"{slug}.html").read_bytes()
        h = sha256_bytes(body)
        src_url = URL_BY_SLUG.get(slug)
        if not src_url:
            print(f"No seed URL in config for slug {slug}", file=sys.stderr)
            sys.exit(1)
        manifest.sources.append(
            SourceRecord(
                source_url=src_url,
                slug=slug,
                outcome=FetchOutcome.FETCHED,
                http_status=200,
                content_hash=h,
                raw_relative_path=f"data/raw/{rid}/{slug}.html",
                byte_size=len(body),
            )
        )

    assert_allowlisted_url(FLEXI_URL)
    flex_slug = slug_from_url(FLEXI_URL)
    print(f"Fetching Flexi Cap: {FLEXI_URL}", flush=True)
    fr = fetch_url_http(FLEXI_URL)
    if fr.outcome != FetchOutcome.FETCHED:
        print(f"HTTP not usable ({fr.outcome}); trying Playwright…", flush=True)
        fr = fetch_url_playwright(FLEXI_URL)
    if fr.outcome != FetchOutcome.FETCHED:
        print(f"Flexi Cap fetch failed: {fr.outcome} {fr.error_message}", file=sys.stderr)
        sys.exit(1)

    flex_html = raw_dst / f"{flex_slug}.html"
    write_bytes(flex_html, fr.body)
    h = sha256_bytes(fr.body)
    html_text = fr.body.decode("utf-8", errors="replace")
    structured = parse_indmoney_html(html_text, FLEXI_URL)
    write_json(proc_dst / f"{flex_slug}.json", structured.model_dump())
    manifest.sources.append(
        SourceRecord(
            source_url=FLEXI_URL,
            slug=flex_slug,
            outcome=FetchOutcome.FETCHED,
            http_status=fr.status_code,
            content_hash=h,
            raw_relative_path=f"data/raw/{rid}/{flex_slug}.html",
            byte_size=len(fr.body),
        )
    )

    manifest.finished_at = datetime.now(timezone.utc)
    manifest.status = "success"
    write_json(manifests_dir() / f"{rid}.json", manifest.model_dump())

    print(f"Ingest merge complete ingest_run_id={rid}", flush=True)
    index_dir = run_phase2_index(rid, backend=args.backend)
    print(f"Index ready -> {index_dir.relative_to(project_root())} backend={args.backend}", flush=True)


if __name__ == "__main__":
    main()
