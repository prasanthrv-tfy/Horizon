"""Tests for content enrichment chain in src/blog/generator/enricher.py"""

import asyncio
from datetime import datetime, timezone

from rich.console import Console

from src.blog.generator.enricher import THIN_CONTENT_THRESHOLD, enrich_thin_items
from src.models import ContentItem


_QUIET = Console(quiet=True)


def make_content_item(id="test:rss:1", content=None) -> ContentItem:
    return ContentItem(
        id=id,
        source_type="rss",
        title="Test Article",
        url="https://example.com/article",
        content=content,
        ai_tags=["ml"],
        published_at=datetime.now(timezone.utc),
    )


def _rich_content() -> str:
    return "x" * THIN_CONTENT_THRESHOLD


def _thin_content() -> str:
    return "short"


# --- enrich_thin_items ---


def test_rich_item_is_not_enriched(monkeypatch):
    """Items with content >= threshold must not trigger fetch or search."""
    fetch_calls = []

    class MockFetcher:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def fetch_url(self, url):
            fetch_calls.append(url)
            return "should not be called"
        def search_fallback(self, title, tags):
            fetch_calls.append("search")
            return ""

    monkeypatch.setattr("src.blog.generator.enricher.ContentFetcher", MockFetcher)

    item = make_content_item(content=_rich_content())
    original_content = item.content
    asyncio.run(enrich_thin_items([item], _QUIET))

    assert item.content == original_content
    assert fetch_calls == []


def test_thin_item_enriched_via_fetch(monkeypatch):
    """Thin items whose URL fetch succeeds get their content replaced."""

    class MockFetcher:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def fetch_url(self, url): return "fetched article content " * 20
        def search_fallback(self, title, tags): return ""

    monkeypatch.setattr("src.blog.generator.enricher.ContentFetcher", MockFetcher)

    item = make_content_item(content=_thin_content())
    asyncio.run(enrich_thin_items([item], _QUIET))

    assert "fetched article content" in item.content


def test_thin_item_falls_back_to_search_on_fetch_failure(monkeypatch):
    """When fetch fails, search_fallback result is used instead."""

    class MockFetcher:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def fetch_url(self, url): raise ConnectionError("timeout")
        def search_fallback(self, title, tags): return "search snippet result " * 10

    monkeypatch.setattr("src.blog.generator.enricher.ContentFetcher", MockFetcher)

    item = make_content_item(content=_thin_content())
    asyncio.run(enrich_thin_items([item], _QUIET))

    assert "search snippet result" in item.content


def test_thin_item_content_unchanged_when_both_fail(monkeypatch):
    """When fetch raises and search returns empty, item content is not modified."""

    class MockFetcher:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def fetch_url(self, url): raise ConnectionError("timeout")
        def search_fallback(self, title, tags): return ""

    monkeypatch.setattr("src.blog.generator.enricher.ContentFetcher", MockFetcher)

    item = make_content_item(content=_thin_content())
    asyncio.run(enrich_thin_items([item], _QUIET))

    assert item.content == _thin_content()


def test_empty_list_does_not_create_fetcher(monkeypatch):
    """Empty input returns immediately without constructing ContentFetcher."""

    def fail_if_instantiated():
        raise AssertionError("ContentFetcher must not be created for empty input")

    monkeypatch.setattr("src.blog.generator.enricher.ContentFetcher", fail_if_instantiated)

    asyncio.run(enrich_thin_items([], _QUIET))  # must not raise
