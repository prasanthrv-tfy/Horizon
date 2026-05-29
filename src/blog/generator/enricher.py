"""Blog-stage content enricher.

Distinct from src/ai/enricher.py (which enriches items for the main pipeline).
This module fetches or search-enriches thin items before blog scoring.
"""

import asyncio
from typing import List

from rich.console import Console

from src.models import ContentItem
from .fetcher import ContentFetcher

THIN_CONTENT_THRESHOLD = 500
_HTML_MARKERS = ("<div", "<p>", "<span", "<!--", "<script", "<img")


def _looks_like_html(text: str) -> bool:
    return any(marker in text for marker in _HTML_MARKERS)


async def _enrich_one(
    item: ContentItem,
    fetcher: ContentFetcher,
    semaphore: asyncio.Semaphore,
    console: Console,
) -> None:
    async with semaphore:
        try:
            text = await fetcher.fetch_url(str(item.url))
            item.content = text
            console.print(f"   [green]✓ fetched[/green] {str(item.url)[:70]}")
            return
        except Exception as fetch_err:
            console.print(
                f"   [yellow]⚠ fetch failed ({fetch_err.__class__.__name__}), using search for:[/yellow] {item.title[:60]}"
            )

        text = fetcher.search_fallback(item.title, item.ai_tags or [])
        if text.strip():
            item.content = text
        else:
            console.print(f"   [red]✗ enrichment failed for:[/red] {item.title[:60]}")


async def enrich_thin_items(items: List[ContentItem], console: Console) -> None:
    """Fetch or search-enrich items whose content is thin or raw HTML."""
    import trafilatura

    needs_enrichment = []
    for it in items:
        content = it.content or ""
        if len(content) < THIN_CONTENT_THRESHOLD:
            needs_enrichment.append(it)
        elif _looks_like_html(content):
            # Content is present but raw HTML — extract in-place without re-fetching
            extracted = trafilatura.extract(content, include_comments=False, include_tables=False) or ""
            if extracted.strip():
                it.content = extracted[:2000]

    if not needs_enrichment:
        return

    console.print(f"🔍 Enriching {len(needs_enrichment)} thin-content items before scoring...")
    semaphore = asyncio.Semaphore(5)
    async with ContentFetcher() as fetcher:
        await asyncio.gather(*[_enrich_one(it, fetcher, semaphore, console) for it in needs_enrichment])
    console.print()
