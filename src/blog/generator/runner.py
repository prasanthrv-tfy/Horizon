"""horizon-blog CLI: reads pipeline output and generates blog posts.

Input file is fixed at artifacts/pipeline-output/important_items.json.
Run `uv run horizon` first to produce that file, then `uv run horizon-blog`.
"""

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from rich.console import Console

from src.ai.client import create_ai_client
from src.models import Config, ContentItem
from src.storage.manager import StorageManager
from .enricher import enrich_thin_items
from .loader import _clean_title, load_important_items, resolve_profiles
from src.blog.models import BlogConfig
from src.blog.profiles import PROFILES
from src.blog.profiles.profile import BlogPromptProfile
from .reporter import _write_ranking_results, _write_run_log
from .scorer import rank_by_relevance, score_items_for_profile
from .writer import BlogWriter

# Fixed input path — run `uv run horizon` to refresh this file
IMPORTANT_ITEMS_PATH = Path("artifacts/pipeline-output/important_items.json")


async def generate_and_save_posts(
    items: List[ContentItem],
    config: Config,
    profile: BlogPromptProfile,
    console: Console,
    blog_scores: dict[str, float] | None = None,
) -> None:
    """Generate blog posts for one profile and write them to disk."""
    if not items:
        console.print("[yellow]No items to process — skipping blog generation.[/yellow]")
        return

    blog_cfg = config.blog or BlogConfig()
    gen_cfg = blog_cfg.generator
    ai_client = create_ai_client(config.ai)
    writer = BlogWriter(
        ai_client,
        profile=profile,
        audience_context=gen_cfg.audience_context,
        platform_context=gen_cfg.platform_context,
    )
    languages = list(config.ai.languages)

    console.print(
        f"📝 [{profile.name}] Generating blog posts for {len(items)} items in {languages}..."
    )
    posts_by_lang = await writer.generate_blog_posts(items, languages)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_dir = Path(gen_cfg.output_dir) / profile.name
    archive_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    for lang, posts in posts_by_lang.items():
        for post in posts:
            safe = re.sub(r'[^\w\s-]', '', post.title.lower())
            safe = re.sub(r'[\s_]+', '-', safe).strip('-')[:60]
            filename = f"{today}-{safe}-{lang}.md"
            archive_path = archive_dir / filename
            archive_path.write_text(post.markdown, encoding="utf-8")

            score = blog_scores.get(post.item_id, post.score) if blog_scores else post.score
            manifest.append({
                "item_id": post.item_id,
                "title": post.title,
                "score": score,
                "tags": post.tags,
                "url": post.url,
                "published_at": post.published_at,
                "language": lang,
                "profile": profile.name,
                "filename": filename,
            })

        console.print(
            f"   {lang.upper()}: {len(posts)} posts → {archive_dir}/"
        )

    manifest_path = archive_dir / "posts.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(len(p) for p in posts_by_lang.values())
    console.print(f"   Total: {total} blog posts generated\n")


async def _run(profile_arg: str | None, rank_only: bool = False, items_arg: str | None = None, all_posts: bool = False, max_posts_arg: int | None = None) -> None:
    load_dotenv()
    console = Console()
    mode_label = "Ranking only" if rank_only else "Starting blog generation"
    console.print(f"[bold cyan]📝 Horizon Blog — {mode_label}...[/bold cyan]\n")

    storage = StorageManager()
    config = storage.load_config()

    items = load_important_items(IMPORTANT_ITEMS_PATH)
    console.print(f"📥 Loaded {len(items)} items from {IMPORTANT_ITEMS_PATH}\n")

    pinned_items = None
    if items_arg:
        try:
            row_nums = [int(n.strip()) for n in items_arg.split(",") if n.strip()]
        except ValueError:
            console.print("[red]✗ --items expects comma-separated integers (e.g. --items 3,7,15)[/red]")
            sys.exit(1)
        invalid = [n for n in row_nums if n < 1 or n > len(items)]
        if invalid:
            console.print(f"[red]✗ Row numbers out of range (1–{len(items)}): {invalid}[/red]")
            sys.exit(1)
        pinned_items = [items[n - 1] for n in row_nums]
        console.print(f"🎯 Pinned {len(pinned_items)} item(s) by row number — skipping scoring gates.\n")
        for n, it in zip(row_nums, pinned_items):
            console.print(f"   {n}. {it.title}")
        console.print()

    blog_cfg = config.blog or BlogConfig()
    gen_cfg = blog_cfg.generator
    max_posts = None if all_posts else (max_posts_arg if max_posts_arg is not None else gen_cfg.max_posts)

    ai_client = create_ai_client(config.ai)

    await enrich_thin_items(items, console)

    profile_name = profile_arg or gen_cfg.profile
    profiles = resolve_profiles(profile_name)
    profiles_scored: dict = {}
    for profile in profiles:
        if pinned_items is not None:
            selected = pinned_items
            blog_scores = None
        elif profile.scoring_dimensions:
            scored = await score_items_for_profile(items, ai_client, console, profile)
            log_path = _write_run_log(scored, profile.name)
            console.print(f"📋 Run log → {log_path}\n")
            profiles_scored[profile.name] = (profile, scored)
            included = sorted(
                (si for si in scored if si.included),
                key=lambda si: si.weighted_sum,
                reverse=True,
            )
            included_slice = included if max_posts is None else included[:max_posts]
            blog_scores = {si.item.id: si.weighted_sum for si in included_slice}
            selected = [si.item for si in included_slice]
            if not selected:
                console.print(f"[yellow]⚠️  [{profile.name}] No items passed the gates — skipping post generation.[/yellow]\n")
                continue
        else:
            ranked = await rank_by_relevance(items, ai_client, console, profile.ranking_context)
            selected = ranked if max_posts is None else ranked[:max_posts]
            blog_scores = None

        console.print(f"🏆  [{profile.name}] Selected top {len(selected)} items:")
        for i, item in enumerate(selected, 1):
            console.print(f"   {i}. {_clean_title(item.title)}")
        console.print()

        if rank_only:
            continue

        await generate_and_save_posts(selected, config, profile, console, blog_scores)

    if profiles_scored:
        _write_ranking_results(profiles_scored, len(items), max_posts)
        console.print("📊 ranking_results.md updated\n")


def main() -> None:
    available = ", ".join(PROFILES.keys())
    parser = argparse.ArgumentParser(description="Generate blog posts from Horizon pipeline output.")
    parser.add_argument(
        "--profile",
        metavar="PROFILE",
        help=f"Prompt profile to use: {available}, or 'all'. Overrides config.json.",
    )
    parser.add_argument(
        "--rank-only",
        action="store_true",
        help="Score and rank items but skip blog post generation.",
    )
    parser.add_argument(
        "--items",
        metavar="ROW_NUMS",
        help="Comma-separated 1-based row numbers of items to generate posts for directly, bypassing scoring gates. Row numbers are shown in the scoring table (run with --rank-only first to see them).",
    )
    parser.add_argument(
        "--all-posts",
        action="store_true",
        help="Generate blog posts for all items that passed the gates, ignoring the max_posts limit in config.",
    )
    parser.add_argument(
        "--max-posts",
        metavar="N",
        type=int,
        help="Maximum number of blog posts to generate. Overrides max_posts in config.json. Ignored if --all-posts is set.",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.profile, rank_only=args.rank_only, items_arg=args.items, all_posts=args.all_posts, max_posts_arg=args.max_posts))
