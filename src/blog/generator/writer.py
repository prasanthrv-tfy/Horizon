"""Blog post generation from high-scoring content items."""

import os
import re
import sys
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, MofNCompleteColumn
from ddgs import DDGS

from src.ai.client import AIClient
from src.ai.utils import parse_json_response
from src.models import ContentItem
from src.blog.models import BlogPost
from src.blog.profiles.profile import BlogPromptProfile


def _sanitize_ddg_query(query: str) -> str:
    """Strip boolean operators and phrase-quotes that DuckDuckGo doesn't handle."""
    q = re.sub(r'\b(OR|AND|NOT)\b', ' ', query)
    q = q.replace('"', '')
    return re.sub(r'\s+', ' ', q).strip()


LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Simplified Chinese (简体中文)",
}


def _safe_format(template: str, **kwargs) -> str:
    """Format a template string, leaving unknown placeholders unchanged.

    Profile prompts may reference placeholders (e.g. {audience_context_section}) that
    some profiles don't define. Plain format_map() would raise KeyError; leaving them
    as-is lets each profile safely omit optional sections.
    """
    class _SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"
    return template.format_map(_SafeDict(**kwargs))


def _split_content(raw: str) -> tuple[str, str]:
    """Split raw item content into (article_text, comments_text).

    HN/Reddit items append a large comment thread after this marker.
    Comments are budgeted separately (3000 chars) so discussion noise
    doesn't crowd out the main article body (8000 chars). If the marker
    is absent the split degrades gracefully — full content, no comments.
    """
    if not raw:
        return "", ""
    if "--- Top Comments ---" in raw:
        main, comments_part = raw.split("--- Top Comments ---", 1)
        return main.strip()[:8000], comments_part.strip()[:3000]
    return raw[:8000], ""


def _build_engagement(meta: dict) -> str:
    """Format item engagement metadata (score, comments, likes, etc.) into a readable string."""
    parts = []
    if meta.get("score"):
        parts.append(f"score: {meta['score']}")
    if meta.get("descendants"):
        parts.append(f"{meta['descendants']} comments")
    if meta.get("favorite_count"):
        parts.append(f"{meta['favorite_count']} likes")
    if meta.get("retweet_count"):
        parts.append(f"{meta['retweet_count']} retweets")
    if meta.get("upvote_ratio"):
        parts.append(f"upvote ratio: {meta['upvote_ratio']:.0%}")
    return ", ".join(parts) if parts else "No engagement data available."


def _build_sources(item: ContentItem, all_results: list) -> str:
    """Build a markdown bullet list of all source URLs (original + web search results)."""
    urls = [str(item.url)] + [r["url"] for r in all_results if r.get("url")]
    return "\n".join(f"- {u}" for u in urls)


def _extract_title(markdown: str, fallback: str) -> str:
    """Extract the first H1 headline from the generated markdown.

    Prefers the AI-generated headline over the raw source title because the AI is
    prompted to write a more SEO-friendly and reader-oriented headline.
    Falls back to `fallback` if no H1 is present on the first non-empty line.
    """
    for line in markdown.split('\n'):
        stripped = line.strip()
        if stripped.startswith('# '):
            return stripped[2:].strip()
        elif stripped:
            break
    return fallback


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
    ) -> AsyncIterator[tuple[str, BlogPost]]:
        """Generate blog posts, yielding (language, post) as each one completes."""
        if not items:
            return

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
                            yield lang, post
                    except Exception as e:
                        print(f"Error generating blog post for {item.id} ({lang}): {e}")
                    progress.advance(task)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(min=2, max=30),
        reraise=True,
    )
    async def _generate_single_post(
        self, item: ContentItem, language: str
    ) -> Optional[BlogPost]:
        """Generate a single blog post for one item in one language."""
        content_text, comments_text = _split_content(item.content or "")
        web_context, all_results = await self._gather_web_context(item, content_text)
        engagement = _build_engagement(item.metadata)
        sources_raw = _build_sources(item, all_results)
        markdown = await self._call_llm(item, language, content_text, comments_text, web_context, engagement)
        sources_section = await self._generate_sources(sources_raw)
        markdown = markdown.rstrip() + "\n\n" + sources_section
        title = _extract_title(markdown, fallback=item.title)
        return BlogPost(
            item_id=item.id,
            title=title,
            markdown=markdown,
            language=language,
            score=item.ai_score or 0,
            url=str(item.url),
            tags=list(item.ai_tags) if item.ai_tags else [],
            published_at=datetime.now(timezone.utc).isoformat(),
        )

    async def _gather_web_context(
        self, item: ContentItem, content_text: str
    ) -> tuple[str, list]:
        """Run web searches for the item and return (formatted web context, raw result list)."""
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
        return web_context, all_results

    async def _generate_sources(self, sources_raw: str) -> str:
        """Generate a labelled ## Sources section from a newline-joined list of raw URLs."""
        from urllib.parse import urlparse

        def _fallback(raw: str) -> str:
            from collections import Counter
            urls = [line.lstrip("- ").strip() for line in raw.splitlines() if line.strip()]
            domain_counts = Counter(urlparse(u).netloc.lstrip("www.") for u in urls)
            lines = []
            for url in urls:
                domain = urlparse(url).netloc.lstrip("www.")
                if domain_counts[domain] > 1:
                    parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
                    qualifier = "/".join(parts[:2])
                    label = f"{domain} ({qualifier})" if qualifier else domain
                else:
                    label = domain or url
                lines.append(f"- [{label}]({url})")
            return "## Sources\n\n" + "\n".join(lines)

        if not sources_raw.strip():
            return ""
        system = (
            "You are formatting a sources list for a tech blog post. "
            "Given a list of URLs, return ONLY a markdown ## Sources section. "
            "Each source on its own line as a markdown link: - [Label](url). "
            "The label must be the site or author name — 1 to 3 words (e.g. 'GitHub', 'MIT News', 'AWS Docs'). "
            "If multiple URLs share the same domain, add a short path qualifier in parentheses to make each label unique "
            "(e.g. for two GitHub repos use 'GitHub (awslabs/mcp)' and 'GitHub (BerriAI/litellm)', not both 'GitHub'). "
            "No explanation, no extra text. Output raw Markdown only."
        )
        try:
            result = (await self.client.complete(
                system=system,
                user=f"URLs:\n{sources_raw}",
                json_mode=False,
            )).strip()
            if not re.search(r'^##\s+[Ss]ources', result, re.MULTILINE):
                result = "## Sources\n\n" + result
            return result
        except Exception:
            return _fallback(sources_raw)

    async def _call_llm(
        self,
        item: ContentItem,
        language: str,
        content_text: str,
        comments_text: str,
        web_context: str,
        engagement: str,
    ) -> str:
        """Build prompts, call the LLM, and return clean markdown (fences stripped)."""
        language_name = LANGUAGE_NAMES.get(language, language)
        comments_section = f"\n**Community Comments:**\n{comments_text}\n" if comments_text else ""

        # Build optional context sections for profiles that support them
        audience_context_section = (
            f"\n**Target audience:** {self.audience_context}\n" if self.audience_context else ""
        )
        platform_context_section = (
            f"\n**Platform context:** {self.platform_context}\n" if self.platform_context else ""
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
        )

        markdown = await self.client.complete(
            system=system_prompt,
            user=user_prompt,
            temperature=0.7,
            max_tokens=8192,
            json_mode=False,
        )

        markdown = markdown.strip()
        # Some LLMs wrap their response in triple-backtick fences despite instructions not to.
        if markdown.startswith("```markdown"):
            markdown = markdown[len("```markdown"):].strip()
        if markdown.startswith("```"):
            markdown = markdown[3:].strip()
        if markdown.endswith("```"):
            markdown = markdown[:-3].strip()
        return markdown

    async def _extract_concepts(self, item: ContentItem, content_text: str) -> List[str]:
        """Generate web search queries using the profile's research prompts."""
        user_prompt = self.profile.research_user.format(
            title=item.title,
            summary=item.ai_summary or item.title,
            tags=", ".join(item.ai_tags) if item.ai_tags else "",
            content=content_text[:2500],
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
        query = _sanitize_ddg_query(query)
        results = None
        try:
            # duckduckgo-search emits debug/warning noise to stderr; scoped redirect avoids
            # polluting the progress bar while leaving other stderr output unaffected.
            stderr = sys.stderr
            sys.stderr = open(os.devnull, "w")
            try:
                ddgs = DDGS()
                results = ddgs.text(query, max_results=max_results)
            finally:
                sys.stderr.close()
                sys.stderr = stderr
        except Exception:
            pass

        if not results:
            print(f"Warning: web search returned no results for: {query[:80]}")
            return []

        return [
            {"title": r.get("title", ""), "url": r.get("href", ""), "body": r.get("body", "")}
            for r in results
        ]
