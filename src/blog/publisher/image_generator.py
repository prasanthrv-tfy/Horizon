import base64
import logging
import os
from typing import List, Optional

import httpx

from src.blog.models import ImageGenerationConfig

logger = logging.getLogger(__name__)

_PROMPT_SYSTEM = (
    "You are a creative director for a technology publication. "
    "Given a blog post title, tags, and SEO description, write a concise image generation prompt "
    "for Stability AI that describes a vivid, photorealistic scene suitable as a featured thumbnail. "
    "The scene must be purely visual — no text, words, labels, or UI elements in the image. "
    "Return ONLY the prompt text, nothing else."
)

_PROMPT_USER_TMPL = "Title: {title}\nTags: {tags}\nSEO description: {seo_description}"


async def generate_image_prompt(
    title: str,
    tags: List[str],
    seo_description: str,
    ai_client,
) -> str:
    """Use the AI client to produce a Stability-optimised visual prompt. Falls back to a template."""
    tags_str = ", ".join(tags) if tags else "technology, AI"
    try:
        response = await ai_client.complete(
            system=_PROMPT_SYSTEM,
            user=_PROMPT_USER_TMPL.format(
                title=title,
                tags=tags_str,
                seo_description=seo_description or title,
            ),
            json_mode=False,
        )
        prompt = response.strip()
        if prompt:
            return prompt
    except Exception as exc:
        logger.warning("Image prompt generation failed for '%s': %s", title, exc)
    return f"Professional tech blog featured image about: {title}. Cinematic lighting, clean composition, no text."


async def generate_image(prompt: str, config: ImageGenerationConfig) -> Optional[bytes]:
    """Call Stability AI via TrueFoundry gateway and return raw PNG bytes, or None on failure."""
    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.warning("openai package not available — skipping image generation")
        return None

    base_url = os.environ.get(config.base_url_env, "")
    api_key = os.environ.get(config.api_key_env, "")

    if not base_url or not api_key:
        logger.warning(
            "Image generation skipped: %s or %s env var not set",
            config.base_url_env,
            config.api_key_env,
        )
        return None

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers={
            "X-TFY-METADATA": "{}",
            "X-TFY-LOGGING-CONFIG": '{"enabled": true}',
        },
    )
    try:
        response = await client.images.generate(
            model=config.model,
            prompt=prompt,
            extra_body={"aspect_ratio": config.aspect_ratio},
        )
        item = response.data[0]
        if item.b64_json:
            return base64.b64decode(item.b64_json)
        if item.url:
            # Some gateway configurations return a URL instead; fetch the bytes
            async with httpx.AsyncClient() as http:
                img_resp = await http.get(item.url)
                img_resp.raise_for_status()
                return img_resp.content
        logger.warning("Image generation returned neither b64_json nor url")
        return None
    except Exception as exc:
        logger.warning("Image generation failed: %s", exc)
        return None
    finally:
        await client.close()
