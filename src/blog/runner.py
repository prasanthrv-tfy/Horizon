"""horizon-blog CLI: reads pipeline output and generates blog posts.

Input file is fixed at data/pipeline-output/important_items.json.
Run `uv run horizon` first to produce that file, then `uv run horizon-blog`.
"""

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
from .models import BlogPost
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
    items: List[ContentItem], config: Config, console: Console
) -> None:
    """Generate blog posts and write them to disk."""
    if not items:
        console.print("[yellow]No items to process — skipping blog generation.[/yellow]")
        return

    blog_cfg = config.blog
    ai_client = create_ai_client(config.ai)
    writer = BlogWriter(ai_client)
    languages = list(config.ai.languages)

    console.print(f"📝 Generating blog posts for {len(items)} items in {languages}...")
    posts_by_lang = await writer.generate_blog_posts(items, languages)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    archive_dir = Path(blog_cfg.output_dir if blog_cfg else "data/blog-posts")

    for lang, posts in posts_by_lang.items():
        for post in posts:
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / f"{today}-{post.slug}-{lang}.md"
            archive_path.write_text(post.markdown, encoding="utf-8")

            posts_dir = Path("docs/_posts")
            posts_dir.mkdir(parents=True, exist_ok=True)
            jekyll_path = posts_dir / f"{today}-{post.slug}-{lang}.md"

            front_matter = (
                "---\n"
                "layout: post\n"
                "type: blog\n"
                f"title: \"{post.title.replace(chr(34), chr(39))}\"\n"
                f"date: {today}\n"
                f"lang: {lang}\n"
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
            f"   {lang.upper()}: {len(posts)} blog posts saved to {archive_dir}/ and docs/_posts/"
        )

    total = sum(len(p) for p in posts_by_lang.values())
    console.print(f"   Total: {total} blog posts generated\n")


async def _run() -> None:
    load_dotenv()
    console = Console()
    console.print("[bold cyan]📝 Horizon Blog — Starting blog generation...[/bold cyan]\n")

    storage = StorageManager()
    config = storage.load_config()

    items = load_important_items(IMPORTANT_ITEMS_PATH)
    console.print(f"📥 Loaded {len(items)} items from {IMPORTANT_ITEMS_PATH}\n")

    blog_cfg = config.blog
    max_posts = blog_cfg.max_posts if blog_cfg else 4

    ai_client = create_ai_client(config.ai)
    items = await rank_by_relevance(items, ai_client, console)

    if len(items) > max_posts:
        items = items[:max_posts]
        console.print(f"🏆 Selected top {max_posts} items by relevance\n")

    await generate_and_save_posts(items, config, console)


def main() -> None:
    asyncio.run(_run())
