from __future__ import annotations

import os
import re
from typing import Any

import httpx

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_SOURCE_URLS = 24


def _allowed_urls_from_hits(hits: list[tuple[dict[str, Any], float]]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for c, _ in hits:
        u = (c.get("source_url") or c.get("canonical_url") or "").strip()
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _chunk_context_block(c: dict[str, Any]) -> str:
    text = (c.get("text") or "").strip()
    if len(text) > 3500:
        text = text[:3497] + "..."
    return (
        f"source_url: {c.get('source_url', '')}\n"
        f"scheme_name: {c.get('scheme_name', '')}\n"
        f"text:\n{text}"
    )


def groq_grounded_answer(user_message: str, hits: list[tuple[dict[str, Any], float]]) -> str | None:
    """
    Draft a short answer using Groq with only retrieved chunk text as grounding.
    Returns None if GROQ_API_KEY is missing or the request fails (caller falls back to templates).
    """
    api_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if not api_key or not hits:
        return None

    allow = _allowed_urls_from_hits(hits)
    context = "\n\n---\n\n".join(_chunk_context_block(c) for c, _ in hits)

    system = (
        "You are FundFacts: a friendly, conversational assistant for Indian mutual fund facts. "
        "Speak naturally (you can say “I”, “here’s”, “looks like”) but stay strictly grounded in the "
        "text under “Indexed excerpts” in the user message. Never use outside or memorized knowledge for numbers or claims. "
        "Do not write “the excerpts”, “indexed documents”, or robotic legalese — instead say things like "
        "“from what’s on the scheme page” or “based on the details we have here”. "
        "If the provided text doesn’t contain the answer, say so in one short warm sentence and suggest what they could ask instead "
        "(e.g. expense ratio, NAV date, exit load) — do not invent facts. "
        "Never recommend which fund to buy, whether to invest, or how to allocate money. "
        "Do not put URLs in your reply. Keep it under 12 sentences, clear paragraphs if helpful."
    )
    user_block = f"Question:\n{user_message.strip()}\n\nIndexed excerpts:\n{context}\n\nAllowed source URLs: {allow}"

    model = (os.environ.get("GROQ_MODEL") or "").strip() or DEFAULT_GROQ_MODEL

    try:
        with httpx.Client(timeout=60.0) as client:
            r = client.post(
                GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_block},
                    ],
                    "temperature": 0.28,
                },
            )
            r.raise_for_status()
            data = r.json()
            text = (data["choices"][0]["message"]["content"] or "").strip()
    except (httpx.HTTPError, KeyError, IndexError, TypeError):
        return None

    if not text:
        return None

    # Strip any URLs the model may have emitted; API returns canonical source separately.
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def is_groq_non_answer(text: str) -> bool:
    """True when the model declined to answer from excerpts; prefer template fallback with raw chunks."""
    t = text.lower()
    needles = (
        "cannot find",
        "can't find",
        "could not find",
        "couldn't find",
        "do not contain",
        "does not contain",
        "don't contain",
        "doesn't contain",
        "not find",
        "no information",
        "not in the provided",
        "not in the indexed",
        "not available in the indexed",
        "not contained in",
    )
    return any(n in t for n in needles)


def all_sources_from_hits(hits: list[tuple[dict[str, Any], float]]) -> tuple[list[str], list]:
    """
    Deduplicated source URLs in retrieval order (up to MAX_SOURCE_URLS), with parallel SourceRef list.
    """
    from mf_chat.schemas import SourceRef

    seen: set[str] = set()
    urls: list[str] = []
    refs: list[SourceRef] = []
    for c, _ in hits:
        u = (c.get("source_url") or c.get("canonical_url") or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        urls.append(u)
        refs.append(SourceRef(url=u, scheme_name=c.get("scheme_name")))
        if len(urls) >= MAX_SOURCE_URLS:
            break
    return urls, refs


def primary_source_from_hits(hits: list[tuple[dict[str, Any], float]]) -> tuple[list[str], list]:
    """First hit only (legacy / tests)."""
    u, r = all_sources_from_hits(hits[:1])
    return u, r
