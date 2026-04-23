from __future__ import annotations

from typing import Any

from mf_chat.groq_client import all_sources_from_hits
from mf_chat.schemas import SourceRef


def source_refs_for_hits(message: str, hits: list[tuple[dict[str, Any], float]]) -> tuple[list[str], list[SourceRef]]:
    """
    Return all distinct source URLs from retrieval hits, in relevance order (deduplicated,
    capped in ``all_sources_from_hits``). ``message`` is kept for API compatibility.
    """
    _ = message
    return all_sources_from_hits(hits)
