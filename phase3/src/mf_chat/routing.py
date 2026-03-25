from __future__ import annotations

import re
from enum import Enum


class Intent(str, Enum):
    FACT = "fact"
    REFUSE_ADVICE = "refuse_advice"
    REFUSE_PERSONAL = "refuse_personal"
    REFUSE_OUT_OF_SCOPE = "refuse_out_of_scope"


AMFI_INDIA_URL = "https://www.amfiindia.com/"
SEBI_INVESTOR_URL = "https://investor.sebi.gov.in/"

REFUSE_ADVICE_ANSWER = (
    "I can’t help with opinions on whether to buy, sell, or hold — or how to size or time trades. "
    "That’s personal/portfolio advice, and I only share neutral facts straight from the scheme pages we’ve indexed "
    "(things like expense ratio, exit load, benchmark, risk label, or SIP minimums). "
    "If you name a fund, ask me a factual question about it and I’ll do my best from those documents.\n\n"
    "For solid background reading: AMFI covers mutual fund basics — "
    f"{AMFI_INDIA_URL}\n"
    "SEBI’s investor site has regulated education on investing safely — "
    f"{SEBI_INVESTOR_URL}"
)

# Educational URLs returned with advice refusals (facts-only boundary + learning resources).
ADVICE_EDUCATION_SOURCE_URLS: tuple[str, ...] = (AMFI_INDIA_URL, SEBI_INVESTOR_URL)

REFUSE_PERSONAL_ANSWER = (
    "I’m sorry — I can’t see or talk about your personal account details, holdings, or tax situation. "
    "Your AMC or RTA portal and your statements are the right place for that."
)

REFUSE_OUT_OF_SCOPE_ANSWER = (
    "I’m focused on straight facts from indexed mutual fund pages — think expense ratio, NAV, benchmark, exit load, SIP minimums, and similar. "
    "Try asking in those terms, or browse AMFI for general learning: "
    f"{AMFI_INDIA_URL}"
)


def classify_message(message: str) -> Intent:
    m = message.strip().lower()
    if not m:
        return Intent.REFUSE_OUT_OF_SCOPE

    # Do not use bare "portfolio" — it matches factual phrases like "portfolio turnover" / "portfolio allocation" in factsheets.
    advice_markers = (
        "recommend",
        "best fund",
        "which fund should",
        "which mutual fund should",
        "what mutual fund should",
        "should i buy",
        "should i sell",
        "should we buy",
        "should we sell",
        "should i invest",
        "should i be investing",
        "where should i invest",
        "where should i put my money",
        "stock tip",
        "what to buy",
        "good investment",
        "top fund",
        "beat the market",
        "my portfolio",
        "your portfolio",
        "build a portfolio",
        "portfolio advice",
        "portfolio construction",
        "rebalance my portfolio",
        "diversify my portfolio",
        "buy or sell",
        "sell or buy",
        "sell or hold",
        "hold or sell",
        "worth buying",
        "worth selling",
        "is it a good time",
        "opinion on",
        "what do you think about",
    )
    if any(x in m for x in advice_markers):
        return Intent.REFUSE_ADVICE

    # Opinionated buy / sell / redeem (avoids missing "should i sell" variants).
    if re.search(
        r"\bshould\s+(i|we)\s+(buy|sell|redeem)\b",
        m,
    ):
        return Intent.REFUSE_ADVICE
    if re.search(
        r"\b(worth it to|better to)\s+(buy|sell)\b",
        m,
    ):
        return Intent.REFUSE_ADVICE

    personal_markers = (
        "my pan",
        "my holdings",
        "my account",
        "my kyc",
        "what is my ",
        "how much did i",
        "my tax",
        "my income",
    )
    if any(x in m for x in personal_markers):
        return Intent.REFUSE_PERSONAL

    if m in {"hi", "hello", "hey", "thanks", "thank you", "ok", "okay"}:
        return Intent.REFUSE_OUT_OF_SCOPE

    return Intent.FACT


def wants_indexed_fund_directory(message: str) -> bool:
    """
    True when the user wants the full catalog: all indexed scheme URLs and names,
    or link listing — not a single-fact lookup. Includes “what can you answer about?” style questions.
    """
    m = re.sub(r"\s+", " ", message.lower().strip())
    if not m:
        return False
    has_scope = (
        "fund" in m
        or "scheme" in m
        or "mutual fund" in m
        or "mutual funds" in m
    )
    if not has_scope:
        return False

    # Coverage / catalog (would otherwise hit Groq + top-1 source and look broken).
    catalog_phrases = (
        "what all mutual funds",
        "what mutual funds can you",
        "which mutual funds can you",
        "what funds can you answer",
        "which funds can you answer",
        "what fund can you answer",
        "how many mutual funds",
        "how many funds can",
        "how many funds do you",
        "mutual funds can you answer",
        "what schemes can you",
        "which schemes can you",
        "what do you know about mutual",
        "what can you tell me about mutual fund",
    )
    if any(p in m for p in catalog_phrases):
        return True
    if "can you answer" in m and ("fund" in m or "scheme" in m):
        return True

    if "indexed" in m or "in the index" in m or "in my index" in m:
        if any(x in m for x in ("list", "all", "which", "what", "show", "every", "url", "link")):
            return True
    if ("all" in m or "every" in m) and ("link" in m or "url" in m):
        return True
    if "list" in m and ("fund" in m or "scheme" in m):
        return True
    if "give" in m and ("link" in m or "url" in m) and ("all" in m or "every" in m):
        return True
    return False
