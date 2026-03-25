from __future__ import annotations

import re
from typing import Any

from mf_chat.groq_client import all_sources_from_hits
from mf_chat.schemas import SourceRef

# Words too generic to pin an answer to one scheme page.
_SCHEME_STOP = frozenset(
    {
        "edelweiss",
        "fund",
        "equity",
        "direct",
        "growth",
        "plan",
        "mutual",
        "the",
        "and",
        "scheme",
        "off",
        "shore",
        "offshore",
        "fof",
        "nav",
        "sip",
        "lumpsum",
        "overview",
    }
)


def _scheme_tokens(scheme_name: str) -> list[str]:
    return [
        w
        for w in re.findall(r"[a-z0-9]+", scheme_name.lower())
        if len(w) > 2 and w not in _SCHEME_STOP
    ]


def _message_mentions_scheme(message: str, scheme_name: str | None) -> bool:
    if not scheme_name:
        return False
    toks = _scheme_tokens(scheme_name)
    if not toks:
        return False
    m = message.lower()
    if len(toks) == 1:
        return toks[0] in m
    return sum(1 for t in toks if t in m) >= 2


def source_refs_for_hits(message: str, hits: list[tuple[dict[str, Any], float]]) -> tuple[list[str], list[SourceRef]]:
    """
    Return citation URLs for this turn.

    - Broad questions (no clear scheme in the query): all distinct scheme URLs from hits, in rank order.
    - Query clearly names one indexed scheme (token overlap): that scheme’s URL only, to avoid noisy extras.
    """
    all_urls, all_refs = all_sources_from_hits(hits)
    if len(all_urls) <= 1:
        return all_urls, all_refs

    matched_by_url: dict[str, SourceRef] = {}
    for c, _ in hits:
        sn = c.get("scheme_name")
        u = (c.get("source_url") or c.get("canonical_url") or "").strip()
        if not u or u in matched_by_url:
            continue
        if _message_mentions_scheme(message, sn):
            matched_by_url[u] = SourceRef(url=u, scheme_name=sn)

    if len(matched_by_url) == 1:
        r = next(iter(matched_by_url.values()))
        return [r.url], [r]

    return all_urls, all_refs
