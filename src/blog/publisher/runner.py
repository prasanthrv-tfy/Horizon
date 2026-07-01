"""horizon-publish CLI: publishes generated blog posts to a CMS.

Run `uv run horizon-blog` first to generate posts, then `uv run horizon-publish`.
Reads from artifacts/blog-posts/*/posts.json manifests.
"""

import asyncio
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from rich.console import Console

from src.ai.client import create_ai_client
from src.storage.manager import StorageManager
from . import create_publisher
from .deduplicator import deduplicate_posts, semantic_is_duplicate
from .converter import wrap_html
from .loader import load_manifest, load_post
from .seo import generate_seo
from .category import assign_category
from .image_generator import generate_image_prompt, generate_image

BLOG_POSTS_DIR = Path("artifacts/blog-posts")
DUMP_HTML_DIR = Path("artifacts/webflow_content")
LOGS_DIR = Path("artifacts/logs")


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


COVER_IMAGES_DIR = Path("artifacts/cover-images")


async def _publish_batch(
    posts: List[Tuple[dict, Path]],
    existing_items_for_dedup: list,
    publisher,
    ai_client,
    console: Console,
    max_publish: int,
    is_draft: bool = True,
    generate_image_flag: bool = False,
    image_gen_config=None,
    site_id: str = "",
    dry_run: bool = False,
    authors: list | None = None,
    categories: list | None = None,
) -> tuple[int, List[Tuple[dict, Path]], int]:
    """Push each post through semantic dedup → SEO → [image] → Webflow.

    Returns (pushed_count, semantic_skipped_list, failed_count).
    """
    console.print(f"📤 Publishing up to {max_publish if max_publish > 0 else 'all'} new post(s)...\n")
    pushed = 0
    failed = 0
    semantic_skipped: List[Tuple[dict, Path]] = []
    wants_image = generate_image_flag or (image_gen_config and image_gen_config.enabled)
    do_image = wants_image and (bool(site_id) or dry_run)

    for entry, base_dir in posts:
        if max_publish > 0 and pushed >= max_publish:
            break

        title = entry.get("title", "")
        console.print(f"   → {title}")

        console.print(f"      checking semantic duplicates...")
        is_dup, matched = await semantic_is_duplicate(title, existing_items_for_dedup, ai_client)
        if is_dup:
            console.print(f"      [dim]⊘ semantic duplicate — matches: {matched!r}[/dim]")
            semantic_skipped.append((entry, base_dir))
            console.print()
            continue

        try:
            post = load_post(entry, base_dir)
            if authors:
                post["author_id"] = random.choice(authors)["id"]
            if categories:
                category_id = await assign_category(
                    title,
                    post.get("tags", []),
                    categories,
                    ai_client,
                )
                if category_id:
                    post["category_id"] = category_id
            console.print(f"      generating SEO...")
            seo = await generate_seo(title, post["markdown"], ai_client)
            post.update(seo)
            console.print(f"      seo_title: {post.get('seo_title', '')!r}")

            if do_image:
                try:
                    console.print(f"      generating cover image...")
                    slug = title.lower().replace(" ", "-")[:40]
                    image_prompt = await generate_image_prompt(
                        title,
                        post.get("tags", []),
                        post.get("seo_description", ""),
                        post.get("markdown", "")[:500],
                        ai_client,
                    )
                    COVER_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
                    (COVER_IMAGES_DIR / f"{slug}.prompt.txt").write_text(image_prompt, encoding="utf-8")
                    console.print(f"      [dim]image prompt saved — {COVER_IMAGES_DIR / f'{slug}.prompt.txt'}[/dim]")
                    image_bytes = await generate_image(image_prompt, image_gen_config)
                    if image_bytes:
                        save_path = COVER_IMAGES_DIR / f"{slug}.png"
                        save_path.write_bytes(image_bytes)
                        console.print(f"      [dim]cover image saved — {save_path}[/dim]")
                        if dry_run:
                            console.print(f"      [dim][dry-run] skipping Webflow upload[/dim]")
                        else:
                            image_asset = await publisher.upload_asset(image_bytes, f"{slug}.png", site_id)
                            if image_asset:
                                post["image_asset"] = image_asset
                                console.print(f"      [dim]cover image uploaded — {image_asset.get('hostedUrl', '')}[/dim]")
                            else:
                                console.print(f"      [yellow]⚠ cover image upload failed — saved locally at {save_path}[/yellow]")
                    else:
                        console.print(f"      [yellow]⚠ cover image generation failed — continuing without image[/yellow]")
                except Exception as img_exc:
                    console.print(f"      [yellow]⚠ cover image error — {img_exc} — continuing without image[/yellow]")

            mode_label = "draft" if is_draft else "live"
            if dry_run:
                console.print(f"      [dim][dry-run] would push {mode_label} to Webflow[/dim]")
            else:
                push_start = datetime.now(tz=timezone.utc)
                console.print(f"      pushing {mode_label} to Webflow...")
                item_id = await publisher.add_draft(post, is_draft=is_draft)
                elapsed_push = (datetime.now(tz=timezone.utc) - push_start).total_seconds()
                console.print(f"      [green]✓ published — id={item_id} ({elapsed_push:.1f}s)[/green]")
                await asyncio.sleep(1)
            pushed += 1
        except Exception as exc:
            console.print(f"      [red]✗ failed — {exc}[/red]")
            failed += 1
        console.print()

    return pushed, semantic_skipped, failed


async def _run(
    console: Console,
    max_publish: int = 0,
    publish: str = "",
    generate_image_flag: bool = False,
    dry_run: bool = False,
) -> None:
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

    image_gen_config = publisher_cfg.image_generation if publisher_cfg else None
    site_id = publisher_cfg.site_id if publisher_cfg else ""
    do_image = generate_image_flag or (image_gen_config and image_gen_config.enabled)
    if do_image and not site_id:
        console.print(
            "[yellow]⚠ Image generation requested but blog.publisher.site_id is not set — "
            "skipping cover image generation.[/yellow]\n"
        )

    ai_client = create_ai_client(config.ai)
    publisher = create_publisher(publisher_cfg, token)
    authors_collection_id = publisher_cfg.authors_collection_id if publisher_cfg else ""
    categories_collection_id = publisher_cfg.categories_collection_id if publisher_cfg else ""

    try:
        run_start = datetime.now(tz=timezone.utc)
        if dry_run:
            console.print("[yellow]⚠ DRY RUN — no changes will be made to Webflow[/yellow]\n")

        authors: list = []
        if authors_collection_id:
            console.print(f"👤 Fetching authors (collection {authors_collection_id})...")
            authors = await publisher.list_authors(authors_collection_id)
            if authors:
                console.print(f"   Found {len(authors)} author(s)\n")
            else:
                console.print("   [yellow]⚠ No authors found — posts will publish without author assignment[/yellow]\n")

        categories: list = []
        if categories_collection_id:
            console.print(f"🏷  Fetching categories (collection {categories_collection_id})...")
            categories = await publisher.list_categories(categories_collection_id)
            if categories:
                console.print(f"   Found {len(categories)} categorie(s)\n")
            else:
                console.print("   [yellow]⚠ No categories found — posts will publish without category assignment[/yellow]\n")

        console.print(f"🔍 Fetching Webflow items (collection {collection_id}, past {dedup_days} day(s))...")
        existing_items = await publisher.list_items(since=since)
        elapsed = (datetime.now(tz=timezone.utc) - run_start).total_seconds()
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
                "description": item.get("fieldData", {}).get("short-description", ""),
            }
            for item in existing_items
            if item.get("fieldData", {}).get("name") or item.get("fieldData", {}).get("short-description")
        ]

        pushed, semantic_skipped, failed = await _publish_batch(
            kept_with_scores,
            existing_items_for_dedup,
            publisher,
            ai_client,
            console,
            max_publish,
            is_draft=(publish or publisher_cfg.publish_mode) != "live",
            generate_image_flag=generate_image_flag,
            image_gen_config=image_gen_config,
            site_id=site_id,
            dry_run=dry_run,
            authors=authors,
            categories=categories,
        )

        total_elapsed = (datetime.now(tz=timezone.utc) - run_start).total_seconds()
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
        "--max-publish",
        metavar="N",
        type=int,
        default=None,
        help="Maximum number of posts to publish. 0 publishes all. Posts are ranked by score; top N are published.",
    )
    parser.add_argument(
        "--publish",
        choices=["draft", "live"],
        metavar="{draft,live}",
        default=None,
        help="Publishing mode. Overrides publish_mode in config. Use 'live' to publish immediately.",
    )
    parser.add_argument(
        "--generate-image",
        action="store_true",
        help="Generate and upload an AI cover image for each post. Overrides image_generation.enabled in config.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview publish without writing to Webflow. Generated cover images are saved to artifacts/cover-images/.",
    )
    args = parser.parse_args()

    load_dotenv()

    # CLI overrides config; fall back to publisher.max_publish from config (0 = all)
    max_publish = args.max_publish
    if max_publish is None:
        from src.storage.manager import StorageManager as _SM
        _cfg = _SM().load_config()
        max_publish = _cfg.blog.publisher.max_publish if (_cfg.blog and _cfg.blog.publisher) else 0

    console = Console(record=True)
    console.print("[bold cyan]📤 Horizon Publish — Starting...[/bold cyan]\n")
    try:
        asyncio.run(_run(
            console,
            max_publish=max_publish,
            publish=args.publish or "",
            generate_image_flag=args.generate_image,
            dry_run=args.dry_run,
        ))
    finally:
        (LOGS_DIR / "plain").mkdir(parents=True, exist_ok=True)
        (LOGS_DIR / "html").mkdir(parents=True, exist_ok=True)
        (LOGS_DIR / "plain" / "publish.log").write_text(console.export_text(clear=False), encoding="utf-8")
        (LOGS_DIR / "html" / "publish.html").write_text(console.export_html(), encoding="utf-8")
