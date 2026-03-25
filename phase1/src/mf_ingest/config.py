from __future__ import annotations

from urllib.parse import urlparse

# Seed scheme pages (IndMoney) — same cohort style for all URLs.
DEFAULT_SEED_URLS: tuple[str, ...] = (
    "https://www.indmoney.com/mutual-funds/edelweiss-emerging-markets-opportunities-equity-offshore-direct-growth-5466",
    "https://www.indmoney.com/mutual-funds/edelweiss-europe-dynamic-equity-offshore-fund-direct-growth-5468",
    "https://www.indmoney.com/mutual-funds/edelweiss-flexi-cap-fund-direct-growth-3174",
    "https://www.indmoney.com/mutual-funds/edelweiss-greater-china-equity-off-shore-fund-direct-plan-growth-5470",
    "https://www.indmoney.com/mutual-funds/edelweiss-us-technology-equity-fund-of-fund-direct-growth-1005498",
)

ALLOWED_FETCH_HOSTS: frozenset[str] = frozenset({"www.indmoney.com"})


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] if path else "unknown"


def assert_allowlisted_url(url: str) -> None:
    host = urlparse(url).netloc.lower()
    if host not in ALLOWED_FETCH_HOSTS:
        raise ValueError(f"URL host not allowlisted for Phase 1 fetch: {host}")
