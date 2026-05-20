"""Blog post generation from high-scoring content items."""

import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, MofNCompleteColumn
from ddgs import DDGS

from ..ai.client import AIClient
from ..ai.utils import parse_json_response
from ..models import ContentItem
from .models import BlogPost
from .profiles.profile import BlogPromptProfile


LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Simplified Chinese (简体中文)",
}


def _safe_format(template: str, **kwargs) -> str:
    """Format a template string, leaving unknown placeholders unchanged."""
    class _SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"
    return template.format_map(_SafeDict(**kwargs))


class BlogWriter:
    """Generates individual blog posts for high-scoring content items."""

    def __init__(self, ai_client: AIClient, profile: BlogPromptProfile,
                 audience_context: str = "", platform_context: str = ""):
        self.client = ai_client
        self.profile = profile
        self.audience_context = audience_context
        self.platform_context = platform_context

    async def generate_blog_posts(
        self,
        items: List[ContentItem],
        languages: List[str],
    ) -> Dict[str, List[BlogPost]]:
        """Generate blog posts for each item in each language."""
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
            task = progress.add_task(f"[{self.profile.name}] Writing blog posts", total=total)

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
        """Generate a single blog post for one item in one language."""
        content_text = ""
        comments_text = ""
        if item.content:
            if "--- Top Comments ---" in item.content:
                main, comments_part = item.content.split("--- Top Comments ---", 1)
                content_text = main.strip()[:8000]
                comments_text = comments_part.strip()[:3000]
            else:
                content_text = item.content[:8000]

        queries = await self._extract_concepts(item, content_text)

        all_results = []
        web_sections = []
        for query in queries:
            results = await self._web_search(query)
            all_results.extend(results)
            if results:
                lines = [f"- [{r['title']}]({r['url']}): {r['body']}" for r in results]
                web_sections.append(f"**{query}:**\n" + "\n".join(lines))
        web_context = "\n\n".join(web_sections) if web_sections else "No web search results available."

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

        sources_list = [str(item.url)]
        for r in all_results:
            if r.get("url"):
                sources_list.append(r["url"])
        sources = "\n".join(f"- {u}" for u in sources_list)

        comments_section = f"\n**Community Comments:**\n{comments_text}\n" if comments_text else ""
        language_name = LANGUAGE_NAMES.get(language, language)

        # Build optional context sections for profiles that support them
        audience_context_section = (
            f"\n**Target audience:** {self.audience_context}\n"
            if self.audience_context else ""
        )
        platform_context_section = (
            f"\n**Platform context:** {self.platform_context}\n"
            if self.platform_context else ""
        )

        system_prompt = _safe_format(
            self.profile.blog_system,
            language_name=language_name,
            audience_context_section=audience_context_section,
            platform_context_section=platform_context_section,
        )
        user_prompt = _safe_format(
            self.profile.blog_user,
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
        """Generate web search queries using the profile's research prompts."""
        user_prompt = self.profile.research_user.format(
            title=item.title,
            summary=item.ai_summary or item.title,
            tags=", ".join(item.ai_tags) if item.ai_tags else "",
            content=content_text[:1000],
        )

        try:
            response = await self.client.complete(
                system=self.profile.research_system,
                user=user_prompt,
                temperature=0.3,
            )
            result = parse_json_response(response)
            return result.get("queries", [])[:3]
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
