"""horizon-blog CLI: reads pipeline output and generates blog posts.

Input file is fixed at data/pipeline-output/important_items.json.
Run `uv run horizon` first to produce that file, then `uv run horizon-blog`.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from rich.console import Console

from ..ai.client import create_ai_client
from ..ai.utils import parse_json_response
from ..models import Config, ContentItem
from ..storage.manager import StorageManager
from .models import BlogConfig, BlogPost
from .profiles import PROFILES
from .profiles.profile import BlogPromptProfile
from .prompts import RELEVANCE_RANKING_SYSTEM, RELEVANCE_RANKING_USER
from .writer import BlogWriter

# Fixed input path — run `uv run horizon` to refresh this file
IMPORTANT_ITEMS_PATH = Path("data/pipeline-output/important_items.json")


def load_important_items(path: Path) -> List[ContentItem]:
    if not path.exists():
        print(
            f"[error] {path} not found. Run `uv run horizon` first to generate it.",
            file=sys.stderr,
        )
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    if not data:
        print("No items in pipeline output. Nothing to do.", file=sys.stderr)
        sys.exit(0)

    return [ContentItem(**item) for item in data]


def resolve_profiles(name: str) -> List[BlogPromptProfile]:
    """Return the list of profiles to run for the given profile name."""
    if name == "all":
        return list(PROFILES.values())
    if name not in PROFILES:
        available = ", ".join(PROFILES.keys())
        print(
            f"[error] Unknown prompt_profile '{name}'. Available profiles: {available}",
            file=sys.stderr,
        )
        sys.exit(1)
    return [PROFILES[name]]


async def rank_by_relevance(
    items: List[ContentItem], ai_client, console: Console
) -> List[ContentItem]:
    """Re-rank items by content relevance using AI."""
    if len(items) <= 1:
        return items

    console.print("🔄 Ranking items by relevance...")

    item_texts = []
    for item in items:
        content_preview = ""
        if item.content:
            content_preview = item.content.split("--- Top Comments ---")[0].strip()[:500]
        item_texts.append(
            f"ID: {item.id}\n"
            f"Title: {item.title}\n"
            f"Summary: {item.ai_summary or item.title}\n"
            f"Tags: {', '.join(item.ai_tags) if item.ai_tags else 'none'}\n"
            f"Content: {content_preview}\n"
        )

    items_text = "\n---\n".join(item_texts)
    user_prompt = RELEVANCE_RANKING_USER.format(
        count=len(items),
        items_text=items_text,
    )

    try:
        response = await ai_client.complete(
            system=RELEVANCE_RANKING_SYSTEM,
            user=user_prompt,
            temperature=0.3,
        )
        result = parse_json_response(response)
        if result and "ranked_ids" in result:
            id_to_item = {item.id: item for item in items}
            ranked = []
            for item_id in result["ranked_ids"]:
                if item_id in id_to_item:
                    ranked.append(id_to_item.pop(item_id))
            ranked.extend(id_to_item.values())
            return ranked
    except Exception as e:
        console.print(f"[yellow]⚠️  Relevance ranking failed ({e}), using original order[/yellow]")

    return items


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


async def _run(profile_arg: str | None) -> None:
    load_dotenv()
    console = Console()
    console.print("[bold cyan]📝 Horizon Blog — Starting blog generation...[/bold cyan]\n")

    storage = StorageManager()
    config = storage.load_config()

    items = load_important_items(IMPORTANT_ITEMS_PATH)
    console.print(f"📥 Loaded {len(items)} items from {IMPORTANT_ITEMS_PATH}\n")

    blog_cfg = config.blog or BlogConfig()
    max_posts = blog_cfg.max_posts

    ai_client = create_ai_client(config.ai)
    items = await rank_by_relevance(items, ai_client, console)

    if len(items) > max_posts:
        items = items[:max_posts]
        console.print(f"🏆 Selected top {max_posts} items by relevance\n")

    profile_name = profile_arg or blog_cfg.prompt_profile
    profiles = resolve_profiles(profile_name)
    for profile in profiles:
        await generate_and_save_posts(items, config, profile, console)


def main() -> None:
    available = ", ".join(PROFILES.keys())
    parser = argparse.ArgumentParser(description="Generate blog posts from Horizon pipeline output.")
    parser.add_argument(
        "--profile",
        metavar="PROFILE",
        help=f"Prompt profile to use: {available}, or 'all'. Overrides config.json.",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.profile))
