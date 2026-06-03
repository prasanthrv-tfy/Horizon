"""horizon-blog CLI: reads pipeline output and generates blog posts.

Input file is fixed at artifacts/pipeline-output/important_items.json.
Run `uv run horizon` first to produce that file, then `uv run horizon-blog`.
"""

import argparse
import asyncio
import json
import random
import re
import sys

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
LOGS_DIR = Path("artifacts/logs")


async def generate_and_save_posts(
    items: List[ContentItem],
    config: Config,
    profile: BlogPromptProfile,
    console: Console,
    blog_scores: dict[str, float] | None = None,
    scored_map: dict | None = None,
) -> dict[str, str]:
    """Generate blog posts for one profile and write them to disk.

    Returns a mapping of item_id -> AI-generated headline for use in ranking results.
    """
    if not items:
        console.print("[yellow]No items to process — skipping blog generation.[/yellow]")
        return {}

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

    archive_dir = Path(gen_cfg.output_dir) / profile.name
    archive_dir.mkdir(parents=True, exist_ok=True)

    console.print(
        f"📝 [{profile.name}] Generating blog posts for {len(items)} items in {languages}..."
    )

    ai_titles: dict[str, str] = {}
    manifest: list[dict] = []
    counts: dict[str, int] = {}
    async for lang, post in writer.generate_blog_posts(items, languages):
        safe = re.sub(r'[^\w\s-]', '', post.title.lower())
        safe = re.sub(r'[\s_]+', '-', safe).strip('-')[:60]
        filename = f"{safe}-{lang}.md"
        archive_path = archive_dir / filename
        archive_path.write_text(post.markdown, encoding="utf-8")

        ai_titles[post.item_id] = post.title
        counts[lang] = counts.get(lang, 0) + 1

        score = blog_scores.get(post.item_id, post.score) if blog_scores else post.score
        si = scored_map.get(post.item_id) if scored_map else None
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
            "inclusion_path": si.inclusion_path if si else None,
            "dimensions": si.dimension_scores if si else {},
        })

    manifest_path = archive_dir / "posts.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    for lang, count in counts.items():
        console.print(f"   {lang.upper()}: {count} posts → {archive_dir}/")
    console.print(f"   Total: {sum(counts.values())} blog posts generated\n")
    return ai_titles


async def _run(profile_arg: str | None, rank_only: bool = False, items_arg: str | None = None, all_posts: bool = False, max_posts_arg: int | None = None) -> None:
    load_dotenv()
    console = Console(record=True)
    mode_label = "Ranking only" if rank_only else "Starting blog generation"
    console.print(f"[bold cyan]📝 Horizon Blog — {mode_label}...[/bold cyan]\n")

    try:
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
        ai_title_maps: dict[str, dict[str, str]] = {}
        for profile in profiles:
            if pinned_items is not None:
                selected = pinned_items
                blog_scores = None
                scored_map = None
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
                if max_posts is None:
                    included_slice = included
                else:
                    path_buckets: dict[str, list] = {}
                    for si in included:
                        key = si.inclusion_path or ""
                        if key not in path_buckets:
                            path_buckets[key] = []
                        path_buckets[key].append(si)
                    if len(path_buckets) <= 1:
                        included_slice = included[:max_posts]
                    else:
                        pool: list = []
                        for bucket in path_buckets.values():
                            pool.extend(bucket[:max_posts])
                        included_slice = random.sample(pool, min(max_posts, len(pool)))
                blog_scores = {si.item.id: si.weighted_sum for si in included_slice}
                scored_map = {si.item.id: si for si in included_slice}
                selected = [si.item for si in included_slice]
                if not selected:
                    console.print(f"[yellow]⚠️  [{profile.name}] No items passed the gates — skipping post generation.[/yellow]\n")
                    continue
            else:
                ranked = await rank_by_relevance(items, ai_client, console, profile.ranking_context)
                selected = ranked if max_posts is None else ranked[:max_posts]
                blog_scores = None
                scored_map = None

            console.print(f"🏆  [{profile.name}] Selected top {len(selected)} items:")
            for i, item in enumerate(selected, 1):
                console.print(f"   {i}. {_clean_title(item.title)}")
            console.print()

            if rank_only:
                continue

            titles = await generate_and_save_posts(selected, config, profile, console, blog_scores, scored_map=scored_map)
            if titles:
                ai_title_maps[profile.name] = titles

        if profiles_scored:
            _write_ranking_results(profiles_scored, len(items), max_posts, ai_title_maps)
            console.print("📊 ranking_results.md updated\n")
    finally:
        (LOGS_DIR / "plain").mkdir(parents=True, exist_ok=True)
        (LOGS_DIR / "html").mkdir(parents=True, exist_ok=True)
        (LOGS_DIR / "plain" / "blog-generation.log").write_text(console.export_text(clear=False), encoding="utf-8")
        (LOGS_DIR / "html" / "blog-generation.html").write_text(console.export_html(), encoding="utf-8")


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

    from src.blog.viewer import generate_results_html
    storage = StorageManager()
    config = storage.load_config()
    blog_cfg = config.blog
    output_dir = Path(blog_cfg.generator.output_dir) if blog_cfg else Path("artifacts/blog-posts")
    html_path = generate_results_html(output_dir, model=config.ai.model)
    Console().print(f"[green]Blog viewer:[/green] {html_path}")
