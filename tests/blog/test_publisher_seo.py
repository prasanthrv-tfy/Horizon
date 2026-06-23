"""Tests for src/blog/publisher/seo.py"""

import asyncio
from unittest.mock import AsyncMock

from src.blog.publisher.seo import generate_seo


def _make_ai_client(response: str):
    client = AsyncMock()
    client.complete = AsyncMock(return_value=response)
    return client


def test_generate_seo_happy_path():
    client = _make_ai_client('{"seo_title": "My Title", "seo_description": "My description."}')
    result = asyncio.run(generate_seo("My Title", "Body text here.", client))
    assert result["seo_title"] == "My Title"
    assert result["seo_description"] == "My description."


def test_generate_seo_strips_markdown_fences():
    response = '```json\n{"seo_title": "Fenced", "seo_description": "Desc."}\n```'
    client = _make_ai_client(response)
    result = asyncio.run(generate_seo("Title", "Body", client))
    assert result["seo_title"] == "Fenced"
    assert result["seo_description"] == "Desc."


def test_generate_seo_truncates_title_to_60():
    long_title = "A" * 80
    client = _make_ai_client(f'{{"seo_title": "{long_title}", "seo_description": "Short."}}')
    result = asyncio.run(generate_seo("Title", "Body", client))
    assert len(result["seo_title"]) <= 60


def test_generate_seo_truncates_description_to_160():
    long_desc = "B" * 200
    client = _make_ai_client(f'{{"seo_title": "Title", "seo_description": "{long_desc}"}}')
    result = asyncio.run(generate_seo("Title", "Body", client))
    assert len(result["seo_description"]) <= 160


def test_generate_seo_fallback_on_invalid_json():
    client = _make_ai_client("not valid json at all")
    result = asyncio.run(generate_seo("Original Title", "Body", client))
    assert result["seo_title"] == "Original Title"
    assert result["seo_description"] == ""


def test_generate_seo_fallback_on_exception():
    client = AsyncMock()
    client.complete = AsyncMock(side_effect=RuntimeError("network error"))
    result = asyncio.run(generate_seo("Original Title", "Body", client))
    assert result["seo_title"] == "Original Title"
    assert result["seo_description"] == ""


def test_generate_seo_fallback_title_truncated_to_60():
    long_title = "X" * 80
    client = AsyncMock()
    client.complete = AsyncMock(side_effect=Exception("boom"))
    result = asyncio.run(generate_seo(long_title, "Body", client))
    assert len(result["seo_title"]) <= 60
