"""Blog-stage content enricher.

Distinct from src/ai/enricher.py (which enriches items for the main pipeline).
This module fetches or search-enriches thin items before blog scoring.
"""

import asyncio
from typing import List

from rich.console import Console

from ...models import ContentItem
from .fetcher import ContentFetcher

THIN_CONTENT_THRESHOLD = 500


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
    """Fetch or search-enrich items whose content is below THIN_CONTENT_THRESHOLD."""
    thin = [it for it in items if len(it.content or "") < THIN_CONTENT_THRESHOLD]
    if not thin:
        return

    console.print(f"🔍 Enriching {len(thin)} thin-content items before scoring...")
    semaphore = asyncio.Semaphore(5)
    async with ContentFetcher() as fetcher:
        await asyncio.gather(*[_enrich_one(it, fetcher, semaphore, console) for it in thin])
    console.print()
