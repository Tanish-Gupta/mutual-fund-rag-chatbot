from __future__ import annotations

import argparse
import sys

from mf_ingest.env_bootstrap import load_project_dotenv
from mf_index.builder import run_phase2_index
from mf_index.paths import project_root
from mf_ingest.config import DEFAULT_SEED_URLS
from mf_ingest.pipeline import run_ingest
from mf_pipeline.schedule import print_schedule_info


def main(argv: list[str] | None = None) -> None:
    load_project_dotenv()
    p = argparse.ArgumentParser(description="Phase 5: ingest (Phase 1) then build search index (Phase 2)")
    p.add_argument(
        "--schedule-info",
        action="store_true",
        help="Print documented GitHub Actions / pipeline schedule and exit",
    )
    p.add_argument("--browser", action="store_true", help="Use Playwright for Phase 1 fetch")
    p.add_argument("--url", action="append", dest="urls", help="Extra seed URL (repeatable)")
    p.add_argument("--no-parse", action="store_true", help="Phase 1: skip structured JSON")
    p.add_argument(
        "--index-backend",
        choices=("chroma", "pinecone"),
        default="chroma",
        help="Phase 2 vector store (default: chroma)",
    )
    p.add_argument("--pinecone-index", default=None, help="Pinecone index name override")
    args = p.parse_args(argv)

    if args.schedule_info:
        print_schedule_info()
        return

    urls = list(DEFAULT_SEED_URLS)
    if args.urls:
        urls.extend(args.urls)

    m = run_ingest(
        urls,
        use_browser=args.browser,
        parse_structured=not args.no_parse,
    )
    rid = m.ingest_run_id
    if args.no_parse:
        print(f"ingest_run_id={rid} status={m.status} (index skipped: --no-parse)")
        if m.status != "success":
            sys.exit(1)
        return

    proc = project_root() / "data" / "processed" / rid
    if not proc.is_dir():
        print(f"No processed dir for {rid}", file=sys.stderr)
        sys.exit(1)

    try:
        index_dir = run_phase2_index(
            rid,
            backend=args.index_backend,
            pinecone_index_name=args.pinecone_index,
        )
    except ImportError as e:
        print(str(e), file=sys.stderr)
        print("Install: pip install -e '.[vector]'", file=sys.stderr)
        sys.exit(1)
    print(
        f"ingest_run_id={rid} status={m.status} phase2 -> {index_dir.relative_to(project_root())} "
        f"backend={args.index_backend}"
    )
    if m.status != "success":
        sys.exit(1)


if __name__ == "__main__":
    main()
