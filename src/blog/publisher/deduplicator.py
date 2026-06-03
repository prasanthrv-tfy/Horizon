import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_SEMANTIC_DEDUP_SYSTEM = """\
You are a blog post deduplication assistant. Given a new blog post title and a list of \
existing published articles (each with a title and a short description), determine whether \
the new post covers the exact same news event or announcement as any existing one.

Respond with JSON only, no other text:
{"is_duplicate": <true|false>, "matched_title": <matched title string or null>}

Guidelines:
- Return is_duplicate=true only if the posts are about the exact same event or release.
- Different coverage angles of the same product (e.g., two unrelated GPT-4 updates months apart) \
are NOT duplicates.
- Ignore differences in wording, framing, or source publication.
- Use the description as the primary signal when the title is vague or edited.
"""

_SEMANTIC_DEDUP_USER = """\
New post title: {new_title}

Existing published articles:
{existing_items}
"""


def normalise_title(title: str) -> str:
    """Lowercase, strip, collapse whitespace, remove punctuation."""
    title = title.lower().strip()
    title = re.sub(r"[^\w\s]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def deduplicate_posts(
    posts: List[Tuple[dict, Path]],
    webflow_items: List[Dict[str, Any]],
) -> Tuple[List[Tuple[dict, Path]], List[Tuple[dict, Path]]]:
    """Return (kept, skipped) — skipped posts have a title already in webflow_items."""
    existing = {
        normalise_title(item.get("fieldData", {}).get("name", ""))
        for item in webflow_items
        if item.get("fieldData", {}).get("name")
    }

    kept: List[Tuple[dict, Path]] = []
    skipped: List[Tuple[dict, Path]] = []
    for entry, base_dir in posts:
        title = entry.get("title", "")
        if normalise_title(title) in existing:
            skipped.append((entry, base_dir))
        else:
            kept.append((entry, base_dir))
    return kept, skipped


_BATCH_DEDUP_SYSTEM = """\
You are a blog post deduplication assistant. Given a list of source news articles and a list \
of already-published blog posts, determine which source articles cover the exact same news event \
or announcement as any published post.

Respond with JSON only, no other text:
{"duplicates": [<0-based indices of source articles that are already covered>]}

Guidelines:
- Mark an article as a duplicate only if it is about the exact same event or release as a published post.
- Different coverage angles of the same product (e.g., two unrelated GPT-4 updates months apart) \
are NOT duplicates.
- Ignore differences in wording, framing, or source publication.
- Use the description/summary as the primary signal when titles are vague or differ.
- If no source articles are duplicates, return {"duplicates": []}.
"""

_BATCH_DEDUP_USER = """\
Source articles to check:
{source_items}

Already published posts:
{published_items}
"""


async def batch_semantic_dedup(
    source_items: List[Dict[str, Any]],
    webflow_items: List[Dict[str, str]],
    ai_client: Any,
) -> set:
    """Check via LLM which source items are already covered by any published Webflow post.

    source_items: list of dicts with 'id', 'title', and 'summary' keys.
    webflow_items: list of dicts with 'title' and 'description' keys.
    Returns a set of source item IDs identified as duplicates. Fails open on any error.
    """
    if not webflow_items:
        return set()
    try:
        src_lines = []
        for i, item in enumerate(source_items):
            src_lines.append(f"{i}. Title: {item.get('title', '')}")
            if item.get("summary"):
                src_lines.append(f"   Summary: {item['summary']}")

        pub_lines = []
        for i, item in enumerate(webflow_items):
            pub_lines.append(f"{i}. Title: {item.get('title', '')}")
            if item.get("description"):
                pub_lines.append(f"   Description: {item['description']}")

        user_prompt = _BATCH_DEDUP_USER.format(
            source_items="\n".join(src_lines),
            published_items="\n".join(pub_lines),
        )
        raw = await ai_client.complete(system=_BATCH_DEDUP_SYSTEM, user=user_prompt)
        data = json.loads(raw)
        duplicate_indices = data.get("duplicates", [])
        return {source_items[i]["id"] for i in duplicate_indices if 0 <= i < len(source_items)}
    except Exception as exc:
        # Fails open: a transient API error should not block publishing valid content.
        # Exact-title dedup already filtered obvious duplicates; semantic is a best-effort second pass.
        logger.warning("Batch semantic dedup failed — treating all as non-duplicate: %s", exc)
        return set()


async def semantic_is_duplicate(
    title: str,
    existing_items: List[Dict[str, str]],
    ai_client: Any,
) -> Tuple[bool, Optional[str]]:
    """Check via LLM whether title covers the same story as any existing item.

    existing_items: list of dicts with 'title' and 'description' keys.
    Returns (is_duplicate, matched_title). Fails open on any error.
    """
    if not existing_items:
        return False, None
    try:
        lines = []
        for i, item in enumerate(existing_items):
            lines.append(f"{i + 1}. Title: {item.get('title', '')}")
            if item.get("description"):
                lines.append(f"   Description: {item['description']}")
        numbered = "\n".join(lines)
        user_prompt = _SEMANTIC_DEDUP_USER.format(new_title=title, existing_items=numbered)
        raw = await ai_client.complete(system=_SEMANTIC_DEDUP_SYSTEM, user=user_prompt)
        data = json.loads(raw)
        is_dup = bool(data.get("is_duplicate", False))
        matched = data.get("matched_title") or None
        return is_dup, matched
    except Exception as exc:
        logger.warning("Semantic dedup check failed for %r — treating as not duplicate: %s", title, exc)
        return False, None
