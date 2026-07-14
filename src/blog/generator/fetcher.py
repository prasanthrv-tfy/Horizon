"""Content fetcher for blog pre-scoring enrichment.

Fetches full article text for items whose RSS content is too thin to score reliably.
Tries a direct URL fetch first (using trafilatura for stable article extraction),
falls back to a DuckDuckGo search on failure.
"""

import os
import sys

import httpx
import trafilatura
from ddgs import DDGS
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

_FETCH_MAX_CHARS = 2000
_SEARCH_MIN_CHARS = 200


def _is_transient_fetch_error(exc: BaseException) -> bool:
    """Retryable: timeouts, dropped connections, and 5xx/429. Not retryable: 4xx (likely bot-block)."""
    if isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return False


# Several news CDNs (Medium, Substack, some paywalled sites) return 403 or bot pages
# without standard browser headers. Spoofing Chrome headers is required for reliable extraction.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def _extract_article_text(html: str) -> str:
    """Extract main article body using trafilatura. Falls back to empty string."""
    text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    return text[:_FETCH_MAX_CHARS]


class ContentFetcher:
    """Fetches or searches for article content to enrich thin RSS items before scoring."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(connect=15.0, read=15.0, write=10.0, pool=10.0),
            headers=_BROWSER_HEADERS,
        )
        return self

    async def __aexit__(self, *_):
        if self._client:
            await self._client.aclose()

    @retry(
        retry=retry_if_exception(_is_transient_fetch_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=0.5, max=5),
    )
    async def fetch_url(self, url: str) -> str:
        """Fetch URL and return article text (first 2000 chars). Raises on failure."""
        if self._client is None:
            raise RuntimeError("ContentFetcher must be used as an async context manager")
        response = await self._client.get(url)
        response.raise_for_status()
        text = _extract_article_text(response.text)
        if len(text) < _SEARCH_MIN_CHARS:
            raise ValueError(f"extracted text too short ({len(text)} chars)")
        return text

    def search_fallback(self, title: str, tags: list[str]) -> str:
        """DuckDuckGo search using title + top 2 tags. Returns concatenated snippets."""
        query = f'{title} {" ".join(tags[:2])}'.strip()
        results = None
        try:
            # duckduckgo-search emits debug/warning noise to stderr that pollutes the progress bar;
            # redirect is scoped tightly here so legitimate errors elsewhere remain visible.
            stderr = sys.stderr
            sys.stderr = open(os.devnull, "w")
            try:
                results = DDGS().text(query, max_results=3)
            finally:
                sys.stderr.close()
                sys.stderr = stderr
        except Exception:
            pass

        if not results:
            print(f"Warning: web search returned no results for: {query[:80]}")
            return ""

        snippets = [
            f"{r.get('title', '')} {r.get('body', '')}".strip()
            for r in results
            if r.get("title") or r.get("body")
        ]
        return " ".join(snippets)