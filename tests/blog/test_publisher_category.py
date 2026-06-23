"""Tests for src/blog/publisher/category.py"""

import asyncio
from unittest.mock import AsyncMock

from src.blog.publisher.category import assign_category


def _make_categories(*names_and_ids):
    """Build a list of category dicts matching Webflow API shape."""
    return [
        {"id": cat_id, "fieldData": {"name": name}}
        for name, cat_id in names_and_ids
    ]


def _make_ai_client(response: str):
    client = AsyncMock()
    client.complete = AsyncMock(return_value=response)
    return client


def test_assign_category_happy_path():
    categories = _make_categories(("AI Research", "id-research"), ("Engineering", "id-eng"))
    client = _make_ai_client('{"category": "AI Research"}')
    result = asyncio.run(assign_category("LLM paper on transformers", ["LLM", "transformers"], categories, client))
    assert result == "id-research"


def test_assign_category_empty_list_returns_none_without_llm_call():
    client = AsyncMock()
    result = asyncio.run(assign_category("Title", ["tag"], [], client))
    assert result is None
    client.complete.assert_not_called()


def test_assign_category_unrecognised_name_returns_none():
    categories = _make_categories(("AI Research", "id-research"))
    client = _make_ai_client('{"category": "NonExistentCategory"}')
    result = asyncio.run(assign_category("Title", [], categories, client))
    assert result is None


def test_assign_category_null_category_returns_none():
    categories = _make_categories(("AI Research", "id-research"))
    client = _make_ai_client('{"category": null}')
    result = asyncio.run(assign_category("Title", [], categories, client))
    assert result is None


def test_assign_category_llm_exception_returns_none():
    categories = _make_categories(("AI Research", "id-research"))
    client = AsyncMock()
    client.complete = AsyncMock(side_effect=RuntimeError("network error"))
    result = asyncio.run(assign_category("Title", ["tag"], categories, client))
    assert result is None


def test_assign_category_invalid_json_returns_none():
    categories = _make_categories(("AI Research", "id-research"))
    client = _make_ai_client("not json")
    result = asyncio.run(assign_category("Title", [], categories, client))
    assert result is None


def test_assign_category_no_usable_name_id_pairs_returns_none():
    # Categories missing fieldData or id
    categories = [{"id": "abc"}, {"fieldData": {"name": "Only Name"}}]
    client = AsyncMock()
    result = asyncio.run(assign_category("Title", [], categories, client))
    assert result is None
    client.complete.assert_not_called()


def test_assign_category_no_tags_still_calls_llm():
    categories = _make_categories(("Engineering", "id-eng"))
    client = _make_ai_client('{"category": "Engineering"}')
    result = asyncio.run(assign_category("Some post", [], categories, client))
    assert result == "id-eng"
    client.complete.assert_called_once()
