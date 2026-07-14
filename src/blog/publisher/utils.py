import json


def parse_llm_json(raw: str) -> dict:
    """Parse a JSON response from an LLM, stripping markdown code fences.

    LLMs sometimes wrap JSON in code fences despite explicit instructions not to.
    """
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(cleaned)
