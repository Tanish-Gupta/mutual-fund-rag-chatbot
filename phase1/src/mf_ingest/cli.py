from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mf_ingest.config import DEFAULT_SEED_URLS
from mf_ingest.env_bootstrap import load_project_dotenv
from mf_ingest.pipeline import ingest_local_html, run_ingest


def main(argv: list[str] | None = None) -> None:
    load_project_dotenv()
    p = argparse.ArgumentParser(description="Phase 1: fetch IndMoney scheme pages + optional structured parse")
    sub = p.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Fetch all default seed URLs (or --url)")
    run_p.add_argument("--url", action="append", dest="urls", help="Extra seed URL (repeatable)")
    run_p.add_argument(
        "--browser",
        action="store_true",
        help="Use Playwright Chromium (needed if site returns Cloudflare challenge)",
    )
    run_p.add_argument(
        "--no-parse",
        action="store_true",
        help="Only store raw HTML; skip structured JSON in data/processed/",
    )
    run_p.add_argument("--run-id", dest="run_id", help="Fixed ingest_run_id (default: random UUID)")

    imp = sub.add_parser("import-html", help="Load HTML saved from browser (when HTTP fetch is blocked)")
    imp.add_argument("file", type=Path, help="Path to saved .html")
    imp.add_argument(
        "--source-url",
        required=True,
        help="Canonical page URL this file came from",
    )
    imp.add_argument(
        "--no-parse",
        action="store_true",
        help="Only copy raw HTML into data/raw/<run_id>/",
    )

    args = p.parse_args(argv)

    if args.cmd == "run":
        urls = list(DEFAULT_SEED_URLS)
        if args.urls:
            urls.extend(args.urls)
        m = run_ingest(
            urls,
            use_browser=args.browser,
            parse_structured=not args.no_parse,
            ingest_run_id=args.run_id,
        )
        print(f"ingest_run_id={m.ingest_run_id} status={m.status}")
        for s in m.sources:
            print(f"  {s.slug}: {s.outcome.value} hash={s.content_hash!s}")
        if m.status != "success":
            sys.exit(1)

    elif args.cmd == "import-html":
        if not args.file.is_file():
            print(f"File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        m = ingest_local_html(
            args.file,
            args.source_url,
            parse_structured=not args.no_parse,
        )
        print(f"ingest_run_id={m.ingest_run_id} status={m.status}")
        for s in m.sources:
            print(f"  {s.slug}: {s.outcome.value}")


if __name__ == "__main__":
    main()
