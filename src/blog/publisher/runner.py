"""horizon-publish CLI: publishes generated blog posts to a CMS.

Run `uv run horizon-blog` first to generate posts, then `uv run horizon-publish`.
Reads from artifacts/blog-posts/*/posts.json manifests.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from rich.console import Console

from src.ai.client import create_ai_client
from src.storage.manager import StorageManager
from .deduplicator import deduplicate_posts, semantic_is_duplicate
from .converter import wrap_html
from .loader import load_manifest, load_post
from .seo import generate_seo
from .webflow import WebflowPublisher

BLOG_POSTS_DIR = Path("artifacts/blog-posts")
DUMP_HTML_DIR = Path("artifacts/webflow_content")


def _collect_posts(console: Console) -> List[Tuple[dict, Path]]:
    """Load all (entry, base_dir) pairs from posts.json manifests."""
    all_posts: List[Tuple[dict, Path]] = []
    for manifest_path in sorted(BLOG_POSTS_DIR.glob("*/posts.json")):
        all_posts.extend(load_manifest(manifest_path))
    return all_posts


def _dump_html(posts: List[Tuple[dict, Path]], console: Console) -> None:
    DUMP_HTML_DIR.mkdir(parents=True, exist_ok=True)
    for entry, base_dir in posts:
        post = load_post(entry, base_dir)
        out = DUMP_HTML_DIR / f"{Path(entry['filename']).stem}.html"
        out.write_text(wrap_html(post), encoding="utf-8")
    console.print(f"[dim]📄 HTML snapshots written to {DUMP_HTML_DIR}[/dim]\n")


async def _run(console: Console, max_drafts: int | None = None) -> None:
    token = os.environ.get("WEBFLOW_TOKEN")
    if not token:
        console.print("[red]✗ WEBFLOW_TOKEN environment variable is not set.[/red]")
        sys.exit(1)

    storage = StorageManager()
    config = storage.load_config()
    blog_cfg = config.blog
    publisher_cfg = blog_cfg.publisher if blog_cfg else None
    collection_id = publisher_cfg.collection_id if publisher_cfg else ""

    if not collection_id:
        console.print(
            "[red]✗ blog.publisher.collection_id is not set in config. "
            "Add it to data/config.json before publishing.[/red]"
        )
        sys.exit(1)

    posts = _collect_posts(console)
    if not posts:
        console.print(
            f"[yellow]⚠️  No blog posts found in {BLOG_POSTS_DIR}. "
            "Run `uv run horizon-blog` first.[/yellow]"
        )
        return

    _dump_html(posts, console)

    console.print(f"📂 Ingesting {len(posts)} local post(s):")
    for entry, base_dir in posts:
        console.print(f"   • {entry.get('profile', '')}/{entry.get('filename', '')}")
    console.print()

    dedup_days = publisher_cfg.deduplication_time_window if publisher_cfg else 14
    since = datetime.now(tz=timezone.utc) - timedelta(days=dedup_days)

    ai_client = create_ai_client(config.ai)
    publisher = WebflowPublisher(token=token, collection_id=collection_id)

    try:
        t0 = datetime.now(tz=timezone.utc)
        console.print(f"🔍 Fetching Webflow items (collection {collection_id}, past {dedup_days} day(s))...")
        existing_items = await publisher.list_items(since=since)
        elapsed = (datetime.now(tz=timezone.utc) - t0).total_seconds()
        console.print(f"   Retrieved {len(existing_items)} existing item(s) in {elapsed:.1f}s\n")

        kept, skipped = deduplicate_posts(posts, existing_items)

        if skipped:
            console.print(f"[dim]⊘  Skipped {len(skipped)} duplicate(s):[/dim]")
            for entry, _ in skipped:
                console.print(f"   [dim]✗ {entry.get('filename', '')}[/dim]")
            console.print()

        if not kept:
            console.print("[yellow]No new posts to publish — all are already in Webflow.[/yellow]")
            return

        # Sort by score descending so the highest-ranked posts are published first
        kept_with_scores = sorted(
            kept,
            key=lambda x: x[0].get("score", 0.0),
            reverse=True,
        )

        # Build existing item list for semantic dedup (title + meta-description)
        existing_items_for_dedup = [
            {
                "title": item.get("fieldData", {}).get("name", ""),
                "description": item.get("fieldData", {}).get("meta-description", ""),
            }
            for item in existing_items
            if item.get("fieldData", {}).get("name") or item.get("fieldData", {}).get("meta-description")
        ]

        console.print(f"📤 Publishing up to {max_drafts if max_drafts is not None else 'all'} new post(s)...\n")
        pushed = 0
        failed = 0
        semantic_skipped: List[Tuple[dict, Path]] = []

        for entry, base_dir in kept_with_scores:
            if max_drafts is not None and pushed >= max_drafts:
                break

            title = entry.get("title", "")
            console.print(f"   → {title}")

            # Semantic dedup check before publishing
            console.print(f"      checking semantic duplicates...")
            is_dup, matched = await semantic_is_duplicate(title, existing_items_for_dedup, ai_client)
            if is_dup:
                console.print(f"      [dim]⊘ semantic duplicate — matches: {matched!r}[/dim]")
                semantic_skipped.append((entry, base_dir))
                console.print()
                continue

            try:
                post = load_post(entry, base_dir)
                console.print(f"      generating SEO...")
                seo = await generate_seo(title, post["markdown"], ai_client)
                post.update(seo)
                console.print(f"      seo_title: {post.get('seo_title', '')!r}")

                t_push = datetime.now(tz=timezone.utc)
                console.print(f"      pushing draft to Webflow...")
                item_id = await publisher.add_draft(post)
                elapsed_push = (datetime.now(tz=timezone.utc) - t_push).total_seconds()
                console.print(f"      [green]✓ published — id={item_id} ({elapsed_push:.1f}s)[/green]")
                pushed += 1
            except Exception as exc:
                console.print(f"      [red]✗ failed — {exc}[/red]")
                failed += 1
            console.print()

        total_elapsed = (datetime.now(tz=timezone.utc) - t0).total_seconds()
        console.print(
            f"📊 Pushed: {pushed}"
            f"  |  Skipped [title]: {len(skipped)}"
            f"  |  Skipped [semantic]: {len(semantic_skipped)}"
            f"  |  Failed: {failed}"
            f"  |  Total time: {total_elapsed:.1f}s"
        )
    finally:
        await publisher.aclose()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Publish generated blog posts to Webflow.")
    parser.add_argument(
        "--max-drafts",
        metavar="N",
        type=int,
        help="Maximum number of drafts to push. Posts are ranked by their blog score; top N are published.",
    )
    args = parser.parse_args()

    load_dotenv()

    # CLI overrides config; fall back to publisher.max_drafts from config
    max_drafts = args.max_drafts
    if max_drafts is None:
        from src.storage.manager import StorageManager as _SM
        _cfg = _SM().load_config()
        if _cfg.blog and _cfg.blog.publisher:
            max_drafts = _cfg.blog.publisher.max_drafts

    console = Console()
    console.print("[bold cyan]📤 Horizon Publish — Starting...[/bold cyan]\n")
    asyncio.run(_run(console, max_drafts=max_drafts))
