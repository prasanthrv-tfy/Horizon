"""horizon-blog CLI: reads pipeline output and generates blog posts.

Input file is fixed at artifacts/pipeline-output/important_items.json.
Run `uv run horizon` first to produce that file, then `uv run horizon-blog`.
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from rich.console import Console

from ..ai.client import create_ai_client
from ..models import Config, ContentItem
from ..storage.manager import StorageManager
from .enricher import enrich_thin_items
from .loader import load_important_items, resolve_profiles
from .models import BlogConfig
from .profiles import PROFILES
from .profiles.profile import BlogPromptProfile
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
) -> None:
    """Generate blog posts for one profile and write them to disk."""
    if not items:
        console.print("[yellow]No items to process — skipping blog generation.[/yellow]")
        return

    blog_cfg = config.blog or BlogConfig()
    ai_client = create_ai_client(config.ai)
    writer = BlogWriter(
        ai_client,
        profile=profile,
        audience_context=blog_cfg.audience_context,
        platform_context=blog_cfg.platform_context,
    )
    languages = list(config.ai.languages)

    console.print(
        f"📝 [{profile.name}] Generating blog posts for {len(items)} items in {languages}..."
    )
    posts_by_lang = await writer.generate_blog_posts(items, languages)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    # Profile-scoped output directory for side-by-side comparison
    archive_dir = Path(blog_cfg.output_dir) / profile.name

    for lang, posts in posts_by_lang.items():
        for post in posts:
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / f"{today}-{post.slug}-{lang}.md"
            archive_path.write_text(post.markdown, encoding="utf-8")

            jekyll_dir = Path("docs/_posts") / profile.name
            jekyll_dir.mkdir(parents=True, exist_ok=True)
            jekyll_path = jekyll_dir / f"{today}-{post.slug}-{lang}.md"

            front_matter = (
                "---\n"
                "layout: post\n"
                "type: blog\n"
                f"title: \"{post.title.replace(chr(34), chr(39))}\"\n"
                f"date: {today}\n"
                f"lang: {lang}\n"
                f"profile: {profile.name}\n"
                f"score: {post.score}\n"
                f"original_url: \"{post.url}\"\n"
                f"tags: [{', '.join(post.tags)}]\n"
                "---\n\n"
            )

            content = post.markdown
            first_line = content.strip().split("\n")[0]
            if first_line.startswith("# "):
                parts = content.split("\n", 1)
                if len(parts) > 1:
                    content = parts[1].strip()

            jekyll_path.write_text(front_matter + content, encoding="utf-8")

        console.print(
            f"   {lang.upper()}: {len(posts)} posts → {archive_dir}/ and docs/_posts/{profile.name}/"
        )

    total = sum(len(p) for p in posts_by_lang.values())
    console.print(f"   Total: {total} blog posts generated\n")


async def _run(profile_arg: str | None, rank_only: bool = False, items_arg: str | None = None, all_posts: bool = False) -> None:
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
    max_posts = None if all_posts else blog_cfg.max_posts

    ai_client = create_ai_client(config.ai)

    await enrich_thin_items(items, console)

    profile_name = profile_arg or blog_cfg.prompt_profile
    profiles = resolve_profiles(profile_name)
    profiles_scored: dict = {}
    for profile in profiles:
        if pinned_items is not None:
            selected = pinned_items
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
            selected = [si.item for si in (included if max_posts is None else included[:max_posts])]
            if not selected:
                console.print(f"[yellow]⚠️  [{profile.name}] No items passed the gates — skipping post generation.[/yellow]\n")
                continue
        else:
            ranked = await rank_by_relevance(items, ai_client, console, profile.ranking_context)
            selected = ranked if max_posts is None else ranked[:max_posts]

        console.print(f"🏆  [{profile.name}] Selected top {len(selected)} items:")
        for i, item in enumerate(selected, 1):
            console.print(f"   {i}. {item.title}")
        console.print()

        if rank_only:
            continue

        await generate_and_save_posts(selected, config, profile, console)

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
    args = parser.parse_args()
    asyncio.run(_run(args.profile, rank_only=args.rank_only, items_arg=args.items, all_posts=args.all_posts))
