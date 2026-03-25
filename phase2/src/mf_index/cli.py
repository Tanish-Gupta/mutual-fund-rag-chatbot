from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mf_ingest.env_bootstrap import load_project_dotenv
from mf_index.builder import run_phase2_index
from mf_index.paths import project_root


def main(argv: list[str] | None = None) -> None:
    load_project_dotenv()
    p = argparse.ArgumentParser(
        description="Phase 2: chunk, embed, and index into Chroma or Pinecone (plus chunks.jsonl audit trail)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser(
        "build",
        help="Embed chunks and upsert to vector DB; write chunks.jsonl + index_manifest.json",
    )
    b.add_argument(
        "--run-id",
        dest="ingest_run_id",
        required=True,
        help="ingest_run_id matching data/processed/<id>/",
    )
    b.add_argument(
        "--backend",
        choices=("chroma", "pinecone"),
        default="chroma",
        help="Vector store: local Chroma (default) or Pinecone (requires PINECONE_API_KEY and index)",
    )
    b.add_argument(
        "--embedding-model",
        default=None,
        help="sentence-transformers model name (default: all-MiniLM-L6-v2)",
    )
    b.add_argument(
        "--pinecone-index",
        default=None,
        help="Pinecone index name (default: env PINECONE_INDEX or mf-rag)",
    )

    args = p.parse_args(argv)

    if args.cmd != "build":
        sys.exit(2)

    root = project_root()
    proc = root / "data" / "processed" / args.ingest_run_id
    if not proc.is_dir():
        print(f"Processed run not found: {proc}", file=sys.stderr)
        sys.exit(1)

    try:
        from mf_index.embeddings import DEFAULT_EMBEDDING_MODEL

        model = args.embedding_model or DEFAULT_EMBEDDING_MODEL
        index_dir = run_phase2_index(
            args.ingest_run_id,
            backend=args.backend,
            embedding_model=model,
            pinecone_index_name=args.pinecone_index,
        )
    except ImportError as e:
        print(str(e), file=sys.stderr)
        print("Install: pip install -e '.[vector]'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Index build failed: {e}", file=sys.stderr)
        sys.exit(1)

    rel = index_dir.relative_to(root)
    print(f"Phase 2 complete -> {rel} (backend={args.backend})")


if __name__ == "__main__":
    main()
