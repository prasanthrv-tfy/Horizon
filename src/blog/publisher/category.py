import logging
from typing import Dict, List, Optional

from .utils import parse_llm_json

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a content categorization assistant. Given a blog post title, its tags, "
    "and a list of available category names, return ONLY a JSON object with one key: "
    "\"category\" (the single best-matching category name from the provided list, exactly as written). "
    "If no category is a reasonable match, return {\"category\": null}. Return nothing else."
)

_USER_TMPL = "Title: {title}\nTags: {tags}\n\nAvailable categories:\n{category_list}"


async def assign_category(
    title: str,
    tags: List[str],
    categories: List[Dict],
    ai_client,
) -> Optional[str]:
    """Pick the best-matching category ID for an article via LLM. Returns None on any failure."""
    if not categories:
        return None

    name_to_id: Dict[str, str] = {
        item.get("fieldData", {}).get("name", ""): item.get("id", "")
        for item in categories
        if item.get("fieldData", {}).get("name") and item.get("id")
    }
    if not name_to_id:
        logger.warning("Categories list has no usable name/id pairs — skipping category assignment")
        return None

    category_list = "\n".join(f"- {name}" for name in name_to_id)
    tags_str = ", ".join(tags) if tags else "(none)"

    try:
        response = await ai_client.complete(
            system=_SYSTEM,
            user=_USER_TMPL.format(title=title, tags=tags_str, category_list=category_list),
        )
        data = parse_llm_json(response)
        matched_name = data.get("category")
        if not matched_name:
            return None
        category_id = name_to_id.get(matched_name)
        if not category_id:
            logger.warning("LLM returned unrecognised category %r — skipping assignment", matched_name)
            return None
        return category_id
    except Exception as exc:
        logger.warning("Category assignment failed for %r: %s", title, exc)
        return None
