"""Tests for src/blog/publisher/deduplicator.py"""

from pathlib import Path

import pytest

from src.blog.publisher.deduplicator import deduplicate_posts, normalise_title


# --- normalise_title ---

def test_normalise_title_lowercase():
    assert normalise_title("GPT-5 Arrives") == "gpt5 arrives"


def test_normalise_title_strips_whitespace():
    assert normalise_title("  hello world  ") == "hello world"


def test_normalise_title_collapses_internal_spaces():
    assert normalise_title("AI   The   Future") == "ai   the   future".replace("   ", " ")


def test_normalise_title_removes_punctuation():
    assert normalise_title("AI: The Future!") == "ai the future"


def test_normalise_title_punctuation_insensitive_match():
    assert normalise_title("AI: The Future!") == normalise_title("AI The Future")


def test_normalise_title_case_insensitive_match():
    assert normalise_title("GPT-5 Arrives") == normalise_title("gpt-5 arrives")


def test_normalise_title_empty():
    assert normalise_title("") == ""


# --- deduplicate_posts ---

def _make_webflow_item(name: str) -> dict:
    return {"id": "abc", "fieldData": {"name": name}}


def test_deduplicate_no_duplicates(tmp_path):
    post = tmp_path / "post.md"
    post.write_text('---\ntitle: "Unique Article"\n---\nContent', encoding="utf-8")
    kept, skipped = deduplicate_posts([post], [_make_webflow_item("Different Article")])
    assert kept == [post]
    assert skipped == []


def test_deduplicate_all_duplicates(tmp_path):
    post = tmp_path / "post.md"
    post.write_text('---\ntitle: "GPT-5 Arrives"\n---\nContent', encoding="utf-8")
    kept, skipped = deduplicate_posts([post], [_make_webflow_item("gpt-5 arrives")])
    assert kept == []
    assert skipped == [post]


def test_deduplicate_partial_duplicates(tmp_path):
    post_a = tmp_path / "post_a.md"
    post_b = tmp_path / "post_b.md"
    post_a.write_text('---\ntitle: "AI: The Future!"\n---\n', encoding="utf-8")
    post_b.write_text('---\ntitle: "A New Model"\n---\n', encoding="utf-8")
    webflow = [_make_webflow_item("AI The Future")]
    kept, skipped = deduplicate_posts([post_a, post_b], webflow)
    assert kept == [post_b]
    assert skipped == [post_a]


def test_deduplicate_empty_posts(tmp_path):
    kept, skipped = deduplicate_posts([], [_make_webflow_item("Something")])
    assert kept == []
    assert skipped == []


def test_deduplicate_empty_webflow(tmp_path):
    post = tmp_path / "post.md"
    post.write_text('---\ntitle: "Some Article"\n---\n', encoding="utf-8")
    kept, skipped = deduplicate_posts([post], [])
    assert kept == [post]
    assert skipped == []


def test_deduplicate_falls_back_to_filename_stem(tmp_path):
    # No front matter title — should use filename stem
    post = tmp_path / "gpt5-arrives-en.md"
    post.write_text("No front matter here\n", encoding="utf-8")
    # Filename stem normalised won't match "Different Article"
    kept, skipped = deduplicate_posts([post], [_make_webflow_item("Different Article")])
    assert kept == [post]
    assert skipped == []
