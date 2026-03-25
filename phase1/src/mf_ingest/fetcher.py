from __future__ import annotations

from dataclasses import dataclass

import httpx

from mf_ingest.models import FetchOutcome


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class FetchResult:
    url: str
    status_code: int | None
    body: bytes
    outcome: FetchOutcome
    error_message: str | None = None


def _is_cloudflare_challenge(html: str) -> bool:
    h = html[:8000].lower()
    return (
        "just a moment" in h
        or "cf-chl" in h
        or "challenge-platform" in h
        or "enable javascript and cookies" in h
    )


def fetch_url_http(url: str, timeout: float = 60.0) -> FetchResult:
    try:
        with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout) as client:
            r = client.get(url)
    except httpx.HTTPError as e:
        return FetchResult(
            url=url,
            status_code=None,
            body=b"",
            outcome=FetchOutcome.ERROR,
            error_message=str(e),
        )

    body = r.content
    text = ""
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        text = ""

    if r.status_code >= 400:
        return FetchResult(
            url=url,
            status_code=r.status_code,
            body=body,
            outcome=FetchOutcome.ERROR,
            error_message=f"HTTP {r.status_code}",
        )

    if _is_cloudflare_challenge(text):
        return FetchResult(
            url=url,
            status_code=r.status_code,
            body=body,
            outcome=FetchOutcome.CLOUDFLARE_CHALLENGE,
            error_message="Cloudflare challenge page (use --browser or save HTML via browser)",
        )

    return FetchResult(url=url, status_code=r.status_code, body=body, outcome=FetchOutcome.FETCHED)


def fetch_url_playwright(url: str, timeout_ms: int = 90_000) -> FetchResult:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError(
            'Playwright not installed. Run: pip install "mf-rag-ingest[browser]" && playwright install chromium'
        ) from e

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            html = page.content()
            body = html.encode("utf-8")
        except Exception as e:
            browser.close()
            return FetchResult(
                url=url,
                status_code=None,
                body=b"",
                outcome=FetchOutcome.ERROR,
                error_message=str(e),
            )
        browser.close()

    if _is_cloudflare_challenge(html):
        return FetchResult(
            url=url,
            status_code=200,
            body=body,
            outcome=FetchOutcome.CLOUDFLARE_CHALLENGE,
            error_message="Still seeing Cloudflare after browser fetch",
        )

    return FetchResult(url=url, status_code=200, body=body, outcome=FetchOutcome.FETCHED)
