from __future__ import annotations

from typing import Any

from pathlib import Path

from mf_chat.groq_client import groq_grounded_answer, is_groq_non_answer
from mf_chat.source_policy import source_refs_for_hits
from mf_chat.paths import latest_index_run_id, project_root
from mf_chat.routing import (
    ADVICE_EDUCATION_SOURCE_URLS,
    AMFI_INDIA_URL,
    REFUSE_ADVICE_ANSWER,
    REFUSE_OUT_OF_SCOPE_ANSWER,
    REFUSE_PERSONAL_ANSWER,
    Intent,
    classify_message,
    wants_indexed_fund_directory,
)
from mf_chat.schemas import ChatResponse, SourceRef
from mf_index.manifest import read_manifest
from mf_index.retrieval import answer_from_chunks, load_chunks, retrieve, retrieve_from_manifest
from mf_ingest.env_bootstrap import load_project_dotenv


def _unique_refs_from_chunks_file(index_path: Path, *, limit: int = 200) -> list[SourceRef]:
    """Distinct scheme page URLs in chunk-store order (first occurrence wins)."""
    chunks = load_chunks(index_path)
    seen: set[str] = set()
    out: list[SourceRef] = []
    for c in chunks:
        u = (c.get("source_url") or c.get("canonical_url") or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(SourceRef(url=u, scheme_name=c.get("scheme_name")))
        if len(out) >= limit:
            break
    return out


def chat(message: str, ingest_run_id: str | None) -> ChatResponse:
    load_project_dotenv()
    msg = message.strip()
    intent = classify_message(msg)

    if intent == Intent.REFUSE_ADVICE:
        advice_sources = [
            SourceRef(url=u, scheme_name=None) for u in ADVICE_EDUCATION_SOURCE_URLS
        ]
        return ChatResponse(
            answer=REFUSE_ADVICE_ANSWER,
            source_urls=list(ADVICE_EDUCATION_SOURCE_URLS),
            sources=advice_sources,
            ingest_run_id="",
        )
    if intent == Intent.REFUSE_PERSONAL:
        return ChatResponse(
            answer=REFUSE_PERSONAL_ANSWER,
            source_urls=[],
            sources=[],
            ingest_run_id="",
        )
    if intent == Intent.REFUSE_OUT_OF_SCOPE:
        return ChatResponse(
            answer=REFUSE_OUT_OF_SCOPE_ANSWER,
            source_urls=[AMFI_INDIA_URL],
            sources=[SourceRef(url=AMFI_INDIA_URL, scheme_name=None)],
            ingest_run_id="",
        )

    rid = ingest_run_id or latest_index_run_id()
    if not rid:
        return ChatResponse(
            answer=(
                "There isn’t a search index in this project yet, so I can’t look anything up. "
                "Once you’ve run ingest and indexing (see the README / mf-pipeline), I’ll be able to answer from your scheme pages."
            ),
            source_urls=[],
            sources=[],
            ingest_run_id="",
        )

    index_dir = project_root() / "data" / "index" / rid
    index_path = index_dir / "chunks.jsonl"
    manifest = read_manifest(index_dir)

    if not index_path.is_file():
        return ChatResponse(
            answer=(
                f"I don’t see chunk data for that ingest run ({rid}). "
                "Rebuild the index with mf-index for that run id when you get a chance."
            ),
            source_urls=[],
            sources=[],
            ingest_run_id=rid,
        )

    if intent == Intent.FACT and wants_indexed_fund_directory(msg):
        refs = _unique_refs_from_chunks_file(index_path)
        if not refs:
            return ChatResponse(
                answer="I looked through this index but didn’t find any scheme URLs to list — you may need to re-run ingest and indexing.",
                source_urls=[],
                sources=[],
                ingest_run_id=rid,
            )
        lines = [f"— {r.scheme_name or 'Scheme'}: {r.url}" for r in refs]
        answer = (
            f"Right now I’m set up with {len(refs)} scheme page(s) in this index. "
            "Pick any of them and ask me a factual question — expense ratio, NAV, exit load, benchmark, risk label, and so on.\n\n"
            + "\n".join(lines)
        )
        return ChatResponse(
            answer=answer,
            source_urls=[r.url for r in refs],
            sources=refs,
            ingest_run_id=rid,
        )

    hits: list[tuple[dict[str, Any], float]]
    if manifest:
        try:
            hits = retrieve_from_manifest(msg, project_root(), manifest, top_k=10)
        except ImportError as e:
            return ChatResponse(
                answer=f"Vector index requires optional dependencies: {e}. Install with pip install -e '.[vector]'",
                source_urls=[],
                sources=[],
                ingest_run_id=rid,
            )
        except RuntimeError as e:
            return ChatResponse(
                answer=f"Vector query failed (check Pinecone env / index): {e}",
                source_urls=[],
                sources=[],
                ingest_run_id=rid,
            )
    else:
        chunks = load_chunks(index_path)
        hits = retrieve(msg, chunks, top_k=10)

    if not hits:
        return ChatResponse(
            answer=(
                "Nothing really matched that query against the indexed pages. "
                "Try a different wording, name the fund if you can, or ask about something concrete like expense ratio, NAV, or exit load."
            ),
            source_urls=[],
            sources=[],
            ingest_run_id=rid,
        )

    groq_text = groq_grounded_answer(msg, hits)
    if groq_text and not is_groq_non_answer(groq_text):
        answer = groq_text
    else:
        answer = answer_from_chunks(msg, hits)

    # Multiple scheme URLs when the question is broad; single URL when the query names one scheme clearly.
    source_urls, sources = source_refs_for_hits(msg, hits)

    return ChatResponse(
        answer=answer,
        source_urls=source_urls,
        sources=sources,
        ingest_run_id=rid,
    )
