from __future__ import annotations

import re
from typing import Any

from mf_index.retrieval import score_chunk

MIN_LEXICAL_OVERLAP = 1.0
MIN_VECTOR_SIMILARITY = 0.36

# Lowercase tokens (from word tokenization) that usually mean “this AMC / house”.
# Keep ambiguous English words out (e.g. “union”, “trust”, “bank”).
KNOWN_INDIAN_MF_AMC_TOKENS: frozenset[str] = frozenset(
    {
        "aditya",
        "axis",
        "bandhan",
        "baroda",
        "birla",
        "canara",
        "dsp",
        "edelweiss",
        "franklin",
        "hdfc",
        "hsbc",
        "icici",
        "idfc",
        "invesco",
        "iti",
        "kotak",
        "lic",
        "mahindra",
        "mirae",
        "motilal",
        "nippon",
        "parag",
        "pgim",
        "pnb",
        "quant",
        "sbi",
        "shriram",
        "sundaram",
        "tata",
        "templeton",
        "uti",
        "whiteoak",
    }
)

AMC_NOT_INDEXED_ANSWER = (
    "That looks like a fund or AMC that isn’t in the indexed scheme pages for this project, "
    "so it’s out of scope here—I can’t pull NAV or other facts for it from this bot’s data."
)

NOT_IN_INDEX_ANSWER = (
    "I couldn’t find this in the indexed scheme pages in a reliable way—the material we have "
    "doesn’t clearly cover what you asked. You can use the source links below to check the "
    "original pages, or try a more specific question (for example expense ratio, exit load, "
    "lock-in, benchmark, risk label, or minimum SIP)."
)


def _word_tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def mentioned_amc_tokens(message: str) -> set[str]:
    return _word_tokens(message) & KNOWN_INDIAN_MF_AMC_TOKENS


def indexed_amc_tokens_from_hits(hits: list[tuple[dict[str, Any], float]]) -> set[str]:
    """AMC tokens that appear in scheme names or canonical URLs of retrieved chunks only."""
    words: set[str] = set()
    for c, _ in hits:
        parts = [
            c.get("scheme_name") or "",
            c.get("source_url") or "",
            c.get("canonical_url") or "",
        ]
        for part in parts:
            words |= _word_tokens(part)
    return words & KNOWN_INDIAN_MF_AMC_TOKENS


def query_names_amc_outside_indexed_hits(message: str, hits: list[tuple[dict[str, Any], float]]) -> bool:
    """
    True when the user names one or more known AMC tokens that never appear in the
    scheme_name / URLs of the retrieval hits (e.g. “HDFC NAV” while the index is only Edelweiss).
    """
    mentioned = mentioned_amc_tokens(message)
    if not mentioned:
        return False
    indexed = indexed_amc_tokens_from_hits(hits)
    return bool(mentioned - indexed)


def best_lexical_overlap(message: str, hits: list[tuple[dict[str, Any], float]]) -> float:
    if not hits:
        return 0.0
    return max(score_chunk(message, (c.get("text") or "")) for c, _ in hits)


def retrieval_seems_relevant(
    message: str,
    hits: list[tuple[dict[str, Any], float]],
    *,
    used_vector: bool,
) -> bool:
    """
    True when retrieved chunks plausibly relate to the question (lexical overlap and/or
    strong vector similarity vs. the query embedding).
    """
    if not hits:
        return False
    best_lx = 0.0
    best_vec = 0.0
    for c, combined in hits:
        text = c.get("text") or ""
        lx = score_chunk(message, text)
        best_lx = max(best_lx, lx)
        if used_vector:
            v = float(combined) - 0.12 * lx
            best_vec = max(best_vec, v)
    if best_lx >= MIN_LEXICAL_OVERLAP:
        return True
    if used_vector and best_vec >= MIN_VECTOR_SIMILARITY:
        return True
    if not used_vector:
        return best_lx >= MIN_LEXICAL_OVERLAP
    return False
