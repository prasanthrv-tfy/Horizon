"""Tests for src/blog/publisher/deduplicator.py"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.blog.publisher.deduplicator import deduplicate_posts, normalise_title, semantic_is_duplicate


# ---------------------------------------------------------------------------
# normalise_title
# ---------------------------------------------------------------------------

def test_normalise_title_lowercase():
    assert normalise_title("GPT-5 Arrives") == "gpt5 arrives"


def test_normalise_title_strips_whitespace():
    assert normalise_title("  hello world  ") == "hello world"


def test_normalise_title_collapses_internal_spaces():
    assert normalise_title("AI   The   Future") == "ai the future"


def test_normalise_title_removes_punctuation():
    assert normalise_title("AI: The Future!") == "ai the future"


def test_normalise_title_punctuation_insensitive_match():
    assert normalise_title("AI: The Future!") == normalise_title("AI The Future")


def test_normalise_title_case_insensitive_match():
    assert normalise_title("GPT-5 Arrives") == normalise_title("gpt-5 arrives")


def test_normalise_title_empty():
    assert normalise_title("") == ""


# ---------------------------------------------------------------------------
# deduplicate_posts helpers
# ---------------------------------------------------------------------------

def _make_webflow_item(name: str, description: str = "") -> dict:
    return {"id": "abc", "fieldData": {"name": name, "meta-description": description}}


def _make_post(title: str, base_dir: Path) -> tuple[dict, Path]:
    return ({"title": title}, base_dir)


# ---------------------------------------------------------------------------
# deduplicate_posts
# ---------------------------------------------------------------------------

def test_deduplicate_no_duplicates(tmp_path):
    post = _make_post("Unique Article", tmp_path)
    kept, skipped = deduplicate_posts([post], [_make_webflow_item("Different Article")])
    assert kept == [post]
    assert skipped == []


def test_deduplicate_all_duplicates(tmp_path):
    post = _make_post("GPT-5 Arrives", tmp_path)
    kept, skipped = deduplicate_posts([post], [_make_webflow_item("gpt-5 arrives")])
    assert kept == []
    assert skipped == [post]


def test_deduplicate_partial_duplicates(tmp_path):
    post_a = _make_post("AI: The Future!", tmp_path)
    post_b = _make_post("A New Model", tmp_path)
    webflow = [_make_webflow_item("AI The Future")]
    kept, skipped = deduplicate_posts([post_a, post_b], webflow)
    assert kept == [post_b]
    assert skipped == [post_a]


def test_deduplicate_empty_posts():
    kept, skipped = deduplicate_posts([], [_make_webflow_item("Something")])
    assert kept == []
    assert skipped == []


def test_deduplicate_empty_webflow(tmp_path):
    post = _make_post("Some Article", tmp_path)
    kept, skipped = deduplicate_posts([post], [])
    assert kept == [post]
    assert skipped == []


def test_deduplicate_normalisation_match(tmp_path):
    # Punctuation and case differences should still match
    post = _make_post("OpenAI: GPT-5 Is Here!", tmp_path)
    kept, skipped = deduplicate_posts([post], [_make_webflow_item("openai gpt5 is here")])
    assert kept == []
    assert skipped == [post]


def test_deduplicate_webflow_item_missing_name(tmp_path):
    # Items without fieldData.name are ignored (not treated as existing)
    post = _make_post("Some Article", tmp_path)
    kept, skipped = deduplicate_posts([post], [{"id": "x", "fieldData": {}}])
    assert kept == [post]
    assert skipped == []


# ---------------------------------------------------------------------------
# semantic_is_duplicate
# ---------------------------------------------------------------------------

def _mock_client(response: dict) -> AsyncMock:
    client = AsyncMock()
    client.complete = AsyncMock(return_value=json.dumps(response))
    return client


def test_semantic_is_duplicate_match():
    client = _mock_client({"is_duplicate": True, "matched_title": "lock-load"})
    existing = [{"title": "lock-load", "description": "MRC is a multipath networking protocol for AI training clusters."}]
    is_dup, matched = asyncio.run(semantic_is_duplicate("Unlocking AI Training Networks with MRC", existing, client))
    assert is_dup is True
    assert matched == "lock-load"


def test_semantic_is_duplicate_no_match():
    client = _mock_client({"is_duplicate": False, "matched_title": None})
    existing = [{"title": "Some other article", "description": "About database indexing."}]
    is_dup, matched = asyncio.run(semantic_is_duplicate("New LLM benchmark released", existing, client))
    assert is_dup is False
    assert matched is None


def test_semantic_is_duplicate_empty_existing():
    client = AsyncMock()
    is_dup, matched = asyncio.run(semantic_is_duplicate("Any title", [], client))
    assert is_dup is False
    assert matched is None
    client.complete.assert_not_called()


def test_semantic_is_duplicate_fails_open_on_invalid_json():
    client = AsyncMock()
    client.complete = AsyncMock(return_value="not json at all")
    existing = [{"title": "Some article", "description": "Some description."}]
    is_dup, matched = asyncio.run(semantic_is_duplicate("Any title", existing, client))
    assert is_dup is False
    assert matched is None


def test_semantic_is_duplicate_fails_open_on_exception():
    client = AsyncMock()
    client.complete = AsyncMock(side_effect=RuntimeError("network error"))
    existing = [{"title": "Some article", "description": "Some description."}]
    is_dup, matched = asyncio.run(semantic_is_duplicate("Any title", existing, client))
    assert is_dup is False
    assert matched is None


def test_semantic_is_duplicate_uses_description_as_signal():
    """LLM receives both title and description — verify prompt includes description."""
    captured_user = {}

    async def capture_complete(system, user):
        captured_user["prompt"] = user
        return json.dumps({"is_duplicate": True, "matched_title": "lock-load"})

    client = AsyncMock()
    client.complete = capture_complete
    existing = [{"title": "lock-load", "description": "MRC networking for AI clusters."}]
    asyncio.run(semantic_is_duplicate("Unlocking MRC", existing, client))
    assert "MRC networking for AI clusters." in captured_user["prompt"]
    assert "lock-load" in captured_user["prompt"]


def test_semantic_is_duplicate_multiple_existing_items():
    """All existing items appear in the prompt; match is found among them."""
    captured_user = {}

    async def capture_complete(system, user):
        captured_user["prompt"] = user
        return json.dumps({"is_duplicate": True, "matched_title": "Article B"})

    client = AsyncMock()
    client.complete = capture_complete
    existing = [
        {"title": "Article A", "description": "About transformer architectures."},
        {"title": "Article B", "description": "Covers MRC multipath networking for GPU clusters."},
        {"title": "Article C", "description": "On reinforcement learning from human feedback."},
    ]
    is_dup, matched = asyncio.run(semantic_is_duplicate("MRC networking deep dive", existing, client))
    assert is_dup is True
    assert matched == "Article B"
    # All three items should appear in the prompt
    assert "Article A" in captured_user["prompt"]
    assert "Article B" in captured_user["prompt"]
    assert "Article C" in captured_user["prompt"]
    assert "transformer architectures" in captured_user["prompt"]
    assert "MRC multipath networking" in captured_user["prompt"]


def test_semantic_is_duplicate_item_without_description():
    """Items with no description still appear in prompt (title only)."""
    captured_user = {}

    async def capture_complete(system, user):
        captured_user["prompt"] = user
        return json.dumps({"is_duplicate": False, "matched_title": None})

    client = AsyncMock()
    client.complete = capture_complete
    existing = [{"title": "Some Article", "description": ""}]
    is_dup, _ = asyncio.run(semantic_is_duplicate("Different topic", existing, client))
    assert is_dup is False
    assert "Some Article" in captured_user["prompt"]
    # Empty description should not add a Description line
    assert "Description:" not in captured_user["prompt"]


def test_semantic_is_duplicate_matched_title_null_in_response():
    """matched_title=null in JSON should return None, not the string 'null'."""
    client = _mock_client({"is_duplicate": False, "matched_title": None})
    existing = [{"title": "Unrelated article", "description": "About database sharding."}]
    is_dup, matched = asyncio.run(semantic_is_duplicate("New benchmark", existing, client))
    assert is_dup is False
    assert matched is None


def test_semantic_is_duplicate_mixed_items_with_and_without_description():
    """Prompt is built correctly when some items have descriptions and some don't."""
    captured_user = {}

    async def capture_complete(system, user):
        captured_user["prompt"] = user
        return json.dumps({"is_duplicate": False, "matched_title": None})

    client = AsyncMock()
    client.complete = capture_complete
    existing = [
        {"title": "Has Description", "description": "Detailed summary here."},
        {"title": "No Description", "description": ""},
    ]
    asyncio.run(semantic_is_duplicate("Some new post", existing, client))
    assert "Has Description" in captured_user["prompt"]
    assert "Detailed summary here." in captured_user["prompt"]
    assert "No Description" in captured_user["prompt"]
