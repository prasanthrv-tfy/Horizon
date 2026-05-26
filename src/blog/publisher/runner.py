"""horizon-publish CLI: publishes generated blog posts to a CMS.

Run `uv run horizon-blog` first to generate posts, then `uv run horizon-publish`.
Reads from docs/_posts/ (Jekyll posts with front matter).
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

from ...ai.client import create_ai_client
from ...storage.manager import StorageManager
from .deduplicator import deduplicate_posts
from .converter import wrap_html
from .loader import load_post
from .seo import generate_seo
from .webflow import WebflowPublisher

JEKYLL_POSTS_DIR = Path("docs/_posts")


DUMP_HTML_DIR = Path("artifacts/webflow_content")


def _dump_html(posts: list[Path], console: Console) -> None:
    DUMP_HTML_DIR.mkdir(parents=True, exist_ok=True)
    for post_path in posts:
        post = load_post(post_path)
        out = DUMP_HTML_DIR / post_path.stem
        out = out.with_suffix(".html")
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

    posts = sorted(JEKYLL_POSTS_DIR.glob("**/*.md")) if JEKYLL_POSTS_DIR.exists() else []
    if not posts:
        console.print(
            f"[yellow]⚠️  No blog posts found in {JEKYLL_POSTS_DIR}. "
            "Run `uv run horizon-blog` first.[/yellow]"
        )
        return

    _dump_html(posts, console)

    console.print(f"📂 Ingesting {len(posts)} local post(s):")
    for p in posts:
        console.print(f"   • {p.relative_to(JEKYLL_POSTS_DIR)}")
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
            for post in skipped:
                console.print(f"   [dim]✗ {post.stem}[/dim]")
            console.print()

        if not kept:
            console.print("[yellow]No new posts to publish — all are already in Webflow.[/yellow]")
            return

        # Sort by front-matter score descending so --max-drafts takes the highest-ranked posts
        kept_with_scores = sorted(
            ((p, load_post(p)["score"]) for p in kept),
            key=lambda x: x[1],
            reverse=True,
        )
        if max_drafts is not None and max_drafts < len(kept_with_scores):
            console.print(
                f"[dim]Ranking {len(kept_with_scores)} post(s) by score, keeping top {max_drafts}:[/dim]"
            )
            for i, (p, score) in enumerate(kept_with_scores, 1):
                marker = "✓" if i <= max_drafts else "✗"
                style = "" if i <= max_drafts else "[dim]"
                end_style = "" if i <= max_drafts else "[/dim]"
                console.print(f"   {style}{marker} #{i} (score={score}) {p.stem}{end_style}")
            console.print()
            kept_with_scores = kept_with_scores[:max_drafts]
        kept_scored = [p for p, _ in kept_with_scores]

        console.print(f"📤 Publishing {len(kept_scored)} new post(s)...\n")
        pushed = 0
        failed = 0

        for post_path in kept_scored:
            try:
                post = load_post(post_path)
                title = post["title"]
                console.print(f"   → {title}")

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
            f"📊 Pushed: {pushed}  |  Skipped (duplicates): {len(skipped)}  |  Failed: {failed}"
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
    console = Console()
    console.print("[bold cyan]📤 Horizon Publish — Starting...[/bold cyan]\n")
    asyncio.run(_run(console, max_drafts=args.max_drafts))
