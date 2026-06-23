import base64
import logging
import os
import random
from typing import Dict, List, Optional, Tuple

import httpx

from src.blog.models import ImageGenerationConfig

logger = logging.getLogger(__name__)

# Authoritative keyword → visual concept mapping.
# Injected as a lookup table into the system prompt; the LLM picks the closest semantic match.
_VISUAL_CONCEPTS: Dict[str, str] = {
    "chart reading":  "an optical element (lens, aperture, eye) focused on structured data (charts, grids, matrices) — machine perception meeting information",
    "unify":          "two distinct forms (streams, paths, shapes) converging into a single point — confluence and integration",
    "reasoning":      "a branching structure (tree, lightning, crystal) that splits and reconverges — thought paths, decision trees",
    "vision":         "layered transparent structure (glass, crystal, lens) with depth revealed — perception seeing through complexity",
    "distillation":   "a wide form (tree, funnel, branches) narrowing to a single concentrated point — refinement to essence",
    "alignment":      "scattered elements (particles, arrows, filings) orienting toward a shared axis — order emerging from chaos",
    "hallucination":  "a confident form at centre fragmenting or dissolving at its edges — coherence giving way to uncertainty",
    "sparsity":       "a mostly empty field with a few precisely placed elements — signal standing out in silence",
    "retrieval":      "a reaching form (tendril, beam, filament) pulling one specific element from a dense background — targeted extraction",
    "scaling":        "identical elements (cubes, dots, tiles) multiplying toward a vanishing point — growth and expansion",
    "calibration":    "a measuring instrument (dial, gauge, ruler) finding its exact position — precision and equilibrium",
    "attention":      "a narrowing beam or spotlight concentrating on a single element in a broader field — selective focus",
    "pruning":        "a structured form (tree, network, graph) with deliberate clean gaps — intentional selective removal",
    "diffusion":      "noise or disorder gradually resolving into recognisable structure — emergence and crystallisation",
    "quantization":   "a continuous form (gradient, wave, curve) collapsing into discrete steps or bands — discretisation",
    "embedding":      "scattered elements compressing toward a dense central cluster — dimensionality and proximity",
    "fine-tuning":    "a rough form being refined toward clean precise edges — iterative improvement and carving",
    "context":        "a narrow opening (keyhole, window, frame) revealing a wider space or landscape beyond — scope and perspective",
    "grounding":      "floating elements connected by taut threads or lines to a solid foundation — anchoring and constraint",
}


def _build_concept_table() -> str:
    return "\n".join(f'- "{k}" → {v}' for k, v in _VISUAL_CONCEPTS.items())


_PROMPT_SYSTEM = (
    "You are a cover image director for a technology publication. "
    "Write a Stability AI image prompt for a cover image representing the given article.\n\n"
    "Step 1 — Find the closest semantic match to the article in this visual concept table:\n"
    + _build_concept_table() +
    "\n\nStep 2 — Choose a specific instantiation of the primary concept that suits the art style "
    "(pick from the options suggested in parentheses, or a similar concrete object). "
    "Flat cartoon/vector styles work with bold iconic shapes; painting styles with textured materials; "
    "graphic design with geometric precision. "
    "Describe only the visual subject and its immediate composition — "
    "NO rooms, interiors, architectural spaces, showcases, lobbies, or display environments. "
    "If a second table entry naturally complements it as a background element without cluttering the frame, include it. "
    "Apply the colour palette to set the mood. "
    "End your prompt with: no text, no logos, no brand marks. "
    "2-3 sentences total. Return ONLY the image-generation prompt text."
)

_PROMPT_USER_TMPL = (
    "Title: {title}\n"
    "Summary: {summary}\n"
    "Tags: {tags}\n"
    "Art style: {art_style}\n"
    "Colour palette: {colour_palette}"
)

# Company name tokens → brand-derived colour palette (no brand names in the image prompt)
_BRAND_PALETTES: List[Tuple[List[str], str]] = [
    (["nvidia", "cuda"],
     "electric green and deep black, high-contrast compute aesthetic"),
    (["microsoft", "azure", "windows", "copilot", "bing"],
     "clean white, corporate blue, cool grey"),
    (["google", "deepmind", "gemini", "bard"],
     "saturated primaries — cobalt blue, coral red, and emerald green"),
    (["anthropic", "claude"],
     "warm amber, off-white, minimal and considered"),
    (["meta", "llama", "facebook"],
     "flat blue, clean white, open documentary feel"),
    (["openai", "gpt", "chatgpt", "sora"],
     "neutral grey-white, cool precision, minimal"),
    (["hugging face", "huggingface"],
     "warm yellow, cream, approachable and open"),
    (["apple"],
     "platinum silver, white, product precision"),
    (["mistral"],
     "deep navy, white, sharp European precision"),
    (["cohere"],
     "coral-orange, white, bold and direct"),
    (["xai", "grok"],
     "stark black and white, high contrast"),
]


def _build_brand_palette(title: str, tags: List[str]) -> str:
    """Return a colour palette hint derived from company names in the title/tags."""
    haystack = (title + " " + " ".join(tags)).lower()
    for keywords, palette in _BRAND_PALETTES:
        if any(kw in haystack for kw in keywords):
            return palette
    return ""


_STYLE_POOL = [
    "digital illustration",
    "abstract digital art",
    "flat vector cartoon illustration",
    "watercolor editorial illustration",
    "neon noir illustration",
    "isometric graphic design",
    "oil painting",
    "comic book pop art illustration",
    "low poly geometric art",
    "synthwave retro art",
    "pencil sketch illustration",
    "surrealist digital collage",
]


def _pick_style() -> str:
    return random.choice(_STYLE_POOL)


async def generate_image_prompt(
    title: str,
    tags: List[str],
    seo_description: str,
    body_excerpt: str,
    ai_client,
) -> str:
    """Generate a Stability-optimised image prompt via semantic lookup against the visual concepts table."""
    tags_str = ", ".join(tags) if tags else "technology, AI"
    art_style = _pick_style()
    colour_palette = _build_brand_palette(title, tags) or "professional, publication-appropriate palette"
    try:
        prompt = (await ai_client.complete(
            system=_PROMPT_SYSTEM,
            user=_PROMPT_USER_TMPL.format(
                title=title,
                summary=seo_description or title,
                tags=tags_str,
                art_style=art_style,
                colour_palette=colour_palette,
            ),
            json_mode=False,
        )).strip()
        if prompt:
            return prompt
    except Exception as exc:
        logger.warning("Image prompt generation failed for '%s': %s", title, exc)
    return f"Editorial illustration for a technology article about: {title}. Single focal point, no text, no UI."


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
