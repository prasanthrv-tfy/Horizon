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
