"""Content fetcher for blog pre-scoring enrichment.

Fetches full article text for items whose RSS content is too thin to score reliably.
Tries a direct URL fetch first; falls back to a DuckDuckGo search on failure.
"""

import os
import sys
from html.parser import HTMLParser

import httpx
from ddgs import DDGS

_FETCH_MAX_CHARS = 2000
_SEARCH_MIN_CHARS = 200

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


class _HTMLTextExtractor(HTMLParser):
    """Minimal HTML-to-text stripper using stdlib html.parser."""

    _SKIP_TAGS = {"script", "style", "noscript", "head", "nav", "footer", "aside"}

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _strip_html(html: str) -> str:
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    return extractor.get_text()


class ContentFetcher:
    """Fetches or searches for article content to enrich thin RSS items before scoring."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=10.0,
            headers=_BROWSER_HEADERS,
        )
        return self

    async def __aexit__(self, *_):
        if self._client:
            await self._client.aclose()

    async def fetch_url(self, url: str) -> str:
        """Fetch URL and return stripped plain text (first 2000 chars). Raises on failure."""
        if self._client is None:
            raise RuntimeError("ContentFetcher must be used as an async context manager")
        response = await self._client.get(url)
        response.raise_for_status()
        text = _strip_html(response.text)[:_FETCH_MAX_CHARS]
        if len(text) < _SEARCH_MIN_CHARS:
            raise ValueError(f"fetched text too short ({len(text)} chars)")
        return text

    def search_fallback(self, title: str, tags: list[str]) -> str:
        """DuckDuckGo search using title + top 2 tags. Returns concatenated snippets."""
        query = f'"{title}" {" ".join(tags[:2])}'.strip()
        try:
            stderr = sys.stderr
            sys.stderr = open(os.devnull, "w")
            try:
                results = DDGS().text(query, max_results=3)
            finally:
                sys.stderr.close()
                sys.stderr = stderr
        except Exception:
            return ""

        snippets = [
            f"{r.get('title', '')} {r.get('body', '')}".strip()
            for r in (results or [])
            if r.get("title") or r.get("body")
        ]
        return " ".join(snippets)