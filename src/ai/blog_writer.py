"""Blog post generation from high-scoring content items.

For each item above the score threshold, generates a standalone Markdown blog post
with web search context and concept extraction.
"""

import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, MofNCompleteColumn
from ddgs import DDGS

from .client import AIClient
from .prompts import (
    CONCEPT_EXTRACTION_SYSTEM, CONCEPT_EXTRACTION_USER,
    BLOG_POST_SYSTEM, BLOG_POST_USER,
)
from .utils import parse_json_response
from ..models import ContentItem


@dataclass
class BlogPost:
    """A generated blog post for a single content item."""

    item_id: str
    title: str
    slug: str
    markdown: str
    language: str
    score: float
    url: str
    tags: List[str] = field(default_factory=list)
    published_at: str = ""


LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Simplified Chinese (简体中文)",
}


class BlogWriter:
    """Generates individual blog posts for high-scoring content items."""

    def __init__(self, ai_client: AIClient):
        self.client = ai_client

    async def generate_blog_posts(
        self,
        items: List[ContentItem],
        languages: List[str],
    ) -> Dict[str, List[BlogPost]]:
        """Generate blog posts for each item in each language.

        Args:
            items: Content items that passed the score threshold
            languages: List of language codes (e.g. ["en", "zh"])

        Returns:
            Dict mapping language code to list of BlogPost objects
        """
        if not items:
            return {lang: [] for lang in languages}

        results: Dict[str, List[BlogPost]] = {lang: [] for lang in languages}
        total = len(items) * len(languages)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("Writing blog posts", total=total)

            for item in items:
                for lang in languages:
                    try:
                        post = await self._generate_single_post(item, lang)
                        if post:
                            results[lang].append(post)
                    except Exception as e:
                        print(f"Error generating blog post for {item.id} ({lang}): {e}")
                    progress.advance(task)

        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=10),
    )
    async def _generate_single_post(
        self, item: ContentItem, language: str
    ) -> Optional[BlogPost]:
        """Generate a single blog post for one item in one language.

        Steps:
        1. Extract concepts needing explanation
        2. Web search for context
        3. Generate blog post via AI
        """
        # Parse content and comments
        content_text = ""
        comments_text = ""
        if item.content:
            if "--- Top Comments ---" in item.content:
                main, comments_part = item.content.split("--- Top Comments ---", 1)
                content_text = main.strip()[:8000]
                comments_text = comments_part.strip()[:3000]
            else:
                content_text = item.content[:8000]

        # Step 1: Concept extraction
        queries = await self._extract_concepts(item, content_text)

        # Step 2: Web search
        all_results = []
        web_sections = []
        for query in queries:
            results = await self._web_search(query)
            all_results.extend(results)
            if results:
                lines = [f"- [{r['title']}]({r['url']}): {r['body']}" for r in results]
                web_sections.append(f"**{query}:**\n" + "\n".join(lines))
        web_context = "\n\n".join(web_sections) if web_sections else "No web search results available."

        # Build engagement string
        meta = item.metadata
        engagement_items = []
        if meta.get("score"):
            engagement_items.append(f"score: {meta['score']}")
        if meta.get("descendants"):
            engagement_items.append(f"{meta['descendants']} comments")
        if meta.get("favorite_count"):
            engagement_items.append(f"{meta['favorite_count']} likes")
        if meta.get("retweet_count"):
            engagement_items.append(f"{meta['retweet_count']} retweets")
        if meta.get("upvote_ratio"):
            engagement_items.append(f"upvote ratio: {meta['upvote_ratio']:.0%}")
        engagement = ", ".join(engagement_items) if engagement_items else "No engagement data available."

        # Build sources list
        sources_list = [str(item.url)]
        for r in all_results:
            if r.get("url"):
                sources_list.append(r["url"])
        sources = "\n".join(f"- {u}" for u in sources_list)

        comments_section = f"\n**Community Comments:**\n{comments_text}\n" if comments_text else ""

        language_name = LANGUAGE_NAMES.get(language, language)

        # Step 3: Generate blog post
        system_prompt = BLOG_POST_SYSTEM.format(language_name=language_name)
        user_prompt = BLOG_POST_USER.format(
            language_name=language_name,
            title=item.title,
            url=str(item.url),
            score=item.ai_score or 0,
            reason=item.ai_reason or "",
            tags=", ".join(item.ai_tags) if item.ai_tags else "",
            content=content_text,
            comments_section=comments_section,
            engagement=engagement,
            web_context=web_context,
            sources=sources,
        )

        markdown = await self.client.complete(
            system=system_prompt,
            user=user_prompt,
            temperature=0.5,
            max_tokens=8192,
            json_mode=False,
        )

        # Clean up markdown — strip wrapping code blocks if present
        markdown = markdown.strip()
        if markdown.startswith("```markdown"):
            markdown = markdown[len("```markdown"):].strip()
        if markdown.startswith("```"):
            markdown = markdown[3:].strip()
        if markdown.endswith("```"):
            markdown = markdown[:-3].strip()

        slug = self._make_slug(item.title)

        return BlogPost(
            item_id=item.id,
            title=item.title,
            slug=slug,
            markdown=markdown,
            language=language,
            score=item.ai_score or 0,
            url=str(item.url),
            tags=list(item.ai_tags) if item.ai_tags else [],
            published_at=datetime.now(timezone.utc).isoformat(),
        )

    async def _extract_concepts(self, item: ContentItem, content_text: str) -> List[str]:
        """Ask AI to identify concepts that need explanation."""
        user_prompt = CONCEPT_EXTRACTION_USER.format(
            title=item.title,
            summary=item.ai_summary or item.title,
            tags=", ".join(item.ai_tags) if item.ai_tags else "",
            content=content_text[:1000],
        )

        try:
            response = await self.client.complete(
                system=CONCEPT_EXTRACTION_SYSTEM,
                user=user_prompt,
                temperature=0.3,
            )
            result = parse_json_response(response)

            queries = result.get("queries", [])
            return queries[:3]
        except Exception as e:
            print(f"Error generating search queries: {e}")
            return []

    async def _web_search(self, query: str, max_results: int = 3) -> list:
        """Search the web for context via DuckDuckGo."""
        try:
            stderr = sys.stderr
            sys.stderr = open(os.devnull, "w")
            try:
                ddgs = DDGS()
                results = ddgs.text(query, max_results=max_results)
            finally:
                sys.stderr.close()
                sys.stderr = stderr
        except Exception as e:
            print(f"Error during web search for '{query}': {e}")
            return []

        return [
            {"title": r.get("title", ""), "url": r.get("href", ""), "body": r.get("body", "")}
            for r in (results or [])
        ]

    @staticmethod
    def _make_slug(title: str) -> str:
        """Generate a URL-safe slug from a title."""
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        return slug[:80]
