"""Tests for src/blog/publisher/loader.py and converter.py"""

from pathlib import Path

from src.blog.publisher.converter import convert_markdown, reading_time
from src.blog.publisher.loader import load_post


# --- convert_markdown ---

def test_convert_markdown_heading():
    html = convert_markdown("# Hello")
    assert "<h1>" in html and "Hello" in html


def test_convert_markdown_paragraph():
    html = convert_markdown("Just a paragraph.")
    assert "<p>" in html


def test_convert_markdown_fenced_code():
    html = convert_markdown("```python\nprint('hi')\n```")
    assert "<code" in html or "<pre" in html


# --- reading_time ---

def test_reading_time_short():
    assert reading_time("a" * 500) == "1 min read"


def test_reading_time_exactly_1000():
    assert reading_time("a" * 1000) == "1 min read"


def test_reading_time_longer():
    assert reading_time("a" * 5000) == "5 min read"


def test_reading_time_empty():
    assert reading_time("") == "1 min read"


# --- load_post ---

_FULL_FM = """\
---
layout: post
type: blog
title: "Test Article Title"
date: 2026-05-26
lang: en
profile: engineer
score: 8.5
original_url: "https://example.com/article"
tags: [AI, Machine Learning, Inference]
---

This is the body content.
"""

_NO_FM = """\
# Just a body

No front matter here at all.
"""


def test_load_post_full_front_matter(tmp_path):
    filename = "2026-05-26-test-article-title-en.md"
    (tmp_path / filename).write_text(_FULL_FM, encoding="utf-8")
    entry = {
        "filename": filename,
        "title": "Test Article Title",
        "url": "https://example.com/article",
        "tags": ["AI", "Machine Learning", "Inference"],
        "published_at": "2026-05-26",
        "score": 8.5,
    }
    post = load_post(entry, tmp_path)
    assert post["title"] == "Test Article Title"
    assert post["url"] == "https://example.com/article"
    assert post["published_at"].startswith("2026-05-26")
    assert "AI" in post["tags"]
    assert post["html"]
    assert "min read" in post["reading_time"]


def test_load_post_no_front_matter(tmp_path):
    filename = "2026-05-26-my-slug-en.md"
    (tmp_path / filename).write_text(_NO_FM, encoding="utf-8")
    entry = {"filename": filename, "published_at": "2026-05-26"}
    post = load_post(entry, tmp_path)
    assert post["published_at"].startswith("2026-05-26")
    assert post["url"] == ""
    assert post["tags"] == []
    assert "<h1>" in post["html"]


def test_load_post_markdown_in_body(tmp_path):
    filename = "2026-05-26-article-en.md"
    (tmp_path / filename).write_text(_FULL_FM, encoding="utf-8")
    entry = {"filename": filename, "title": "Article"}
    post = load_post(entry, tmp_path)
    assert "body content" in post["markdown"]
