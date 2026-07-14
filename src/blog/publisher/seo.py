import logging

from .utils import parse_llm_json

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are an SEO expert. Given a blog post title and body, return ONLY a JSON object "
    "with two keys: \"seo_title\" (≤60 characters, compelling search title) and "
    "\"seo_description\" (≤160 characters, concise meta description for search engines). "
    "Return nothing else."
)

_USER_TMPL = "Title: {title}\n\nBody (excerpt):\n{excerpt}"


async def generate_seo(title: str, markdown: str, ai_client) -> dict:
    """Generate SEO title and description via AI. Falls back gracefully on failure."""
    excerpt = markdown[:1500]
    try:
        response = await ai_client.complete(
            system=_SYSTEM,
            user=_USER_TMPL.format(title=title, excerpt=excerpt),
        )
        data = parse_llm_json(response)
        seo_title = str(data.get("seo_title", title))[:60]
        seo_description = str(data.get("seo_description", ""))[:160]
        return {"seo_title": seo_title, "seo_description": seo_description}
    except Exception as exc:
        logger.warning("SEO generation failed for '%s': %s", title, exc)
        return {"seo_title": title[:60], "seo_description": ""}
