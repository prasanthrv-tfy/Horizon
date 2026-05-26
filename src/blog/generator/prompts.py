ITEM_SCORING_SYSTEM = """You are an expert content curator scoring news items for a specific audience.

You will be given a list of news items and a set of scoring dimensions. For each item, score it on every dimension from 0 to 10 and provide a concise reason (one sentence) for each score.

Use the anchor descriptions for each dimension to calibrate your scores — they define what specific score values mean for that dimension. Be consistent: if two items are equally relevant, give them the same score.

Return valid JSON only. No prose outside the JSON.
"""

ITEM_SCORING_USER = """Score the following {count} news items on each dimension below.

## Dimensions

{dimensions_text}

## Items

{items_text}

Respond with valid JSON only:
{{
  "items": [
    {{
      "id": "<item id>",
      "dimensions": {{
        "<dimension_name>": {{"score": <0-10>, "reason": "<one sentence>"}}
      }}
    }}
  ]
}}"""

RELEVANCE_RANKING_SYSTEM = """You are an expert content curator ranking news items by relevance for a specific audience.

{audience_context_block}

Do NOT use the numeric score provided — make your own independent judgment based on the content.

Return a JSON array of item IDs ordered from most to least relevant:
{{"ranked_ids": ["id1", "id2", "id3", ...]}}
"""

RELEVANCE_RANKING_SYSTEM_DEFAULT_CRITERIA = """Given a list of news items (each with a title, summary, tags, and content snippet), rank them from MOST to LEAST relevant based on:

- **Newsworthiness**: How significant is this development? Does it represent a genuine breakthrough, major release, or important shift?
- **Originality**: Is this an original source or primary announcement, versus derivative commentary?
- **Breadth of impact**: How many people/projects/industries does this affect?
- **Timeliness**: Is this breaking news or a developing story versus old news resurfacing?
- **Technical substance**: Does the content have real technical depth, data, or concrete details?
- **Community signal**: Strong community engagement with substantive discussion indicates higher relevance."""

RELEVANCE_RANKING_USER = """Rank the following {count} news items from MOST to LEAST relevant. Return ONLY a JSON object with a "ranked_ids" array.

{items_text}

Respond with valid JSON only:
{{"ranked_ids": ["<most relevant id>", ..., "<least relevant id>"]}}"""
