"""Tests for WebflowPublisher.add_draft() field mapping."""

import asyncio
import json
import re
import httpx

from src.blog.publisher.webflow import WebflowPublisher, _make_slug

_WEBFLOW_SLUG_RE = re.compile(r'(^$)|^[_a-zA-Z0-9][-_a-zA-Z0-9]*$')


def _make_capturing_publisher(captured: dict, image_field="thumbnail-image",
                               author_field="author", category_field="categories"):
    """Build a publisher that records the request body sent to Webflow."""
    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "new-item-id"})

    transport = httpx.MockTransport(handler)
    publisher = WebflowPublisher.__new__(WebflowPublisher)
    publisher._collection_id = "col123"
    publisher._image_field = image_field
    publisher._author_field = author_field
    publisher._category_field = category_field
    publisher._client = httpx.AsyncClient(
        base_url="https://api.webflow.com/v2",
        transport=transport,
    )
    return publisher


def _make_error_publisher(status: int):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text="Error")

    transport = httpx.MockTransport(handler)
    publisher = WebflowPublisher.__new__(WebflowPublisher)
    publisher._collection_id = "col123"
    publisher._image_field = "cover-image"
    publisher._author_field = "author"
    publisher._category_field = "categories"
    publisher._client = httpx.AsyncClient(
        base_url="https://api.webflow.com/v2",
        transport=transport,
    )
    return publisher


def test_add_draft_field_names_match_schema():
    captured = {}
    publisher = _make_capturing_publisher(captured)
    asyncio.run(publisher.add_draft({
        "title": "Test Post",
        "seo_title": "SEO Title",
        "seo_description": "SEO Desc",
        "html": "<p>body</p>",
        "published_at": "2026-06-23T00:00:00Z",
        "reading_time": "3 min read",
    }))
    fd = captured["body"]["fieldData"]
    assert "random" in fd
    assert "short-description" in fd
    assert "news-description" in fd
    assert "date" in fd
    assert fd["featured-on-top"] is False
    assert fd["latest-news"] is True
    assert fd["main-hero-news"] is False
    assert fd["highlighted-news"] is False
    assert fd["premium-content"] is False
    # Removed fields must not appear
    assert "meta-title" not in fd
    assert "meta-description" not in fd
    assert "description" not in fd
    assert "content" not in fd
    assert "published-date" not in fd
    assert "focus-articles" not in fd


def test_add_draft_author_id_injected():
    captured = {}
    publisher = _make_capturing_publisher(captured)
    asyncio.run(publisher.add_draft({"title": "T", "author_id": "author-abc"}))
    assert captured["body"]["fieldData"]["author"] == "author-abc"


def test_add_draft_author_id_absent_key_not_present():
    captured = {}
    publisher = _make_capturing_publisher(captured)
    asyncio.run(publisher.add_draft({"title": "T"}))
    assert "author" not in captured["body"]["fieldData"]


def test_add_draft_category_id_injected():
    captured = {}
    publisher = _make_capturing_publisher(captured, category_field="category-2")
    asyncio.run(publisher.add_draft({"title": "T", "category_id": "cat-xyz"}))
    assert captured["body"]["fieldData"]["category-2"] == "cat-xyz"


def test_add_draft_category_id_absent_key_not_present():
    captured = {}
    publisher = _make_capturing_publisher(captured)
    asyncio.run(publisher.add_draft({"title": "T"}))
    assert "categories" not in captured["body"]["fieldData"]


def test_add_draft_image_asset_injected():
    captured = {}
    publisher = _make_capturing_publisher(captured)
    asyncio.run(publisher.add_draft({
        "title": "T",
        "image_asset": {"id": "img-id", "hostedUrl": "https://cdn.example.com/img.png"},
    }))
    img = captured["body"]["fieldData"]["thumbnail-image"]
    assert img["fileId"] == "img-id"
    assert img["url"] == "https://cdn.example.com/img.png"


def test_add_draft_returns_webflow_item_id():
    captured = {}
    publisher = _make_capturing_publisher(captured)
    item_id = asyncio.run(publisher.add_draft({"title": "T"}))
    assert item_id == "new-item-id"


def test_add_draft_raises_on_api_error():
    publisher = _make_error_publisher(422)
    try:
        asyncio.run(publisher.add_draft({"title": "T"}))
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "422" in str(exc)


def _make_slug_collision_publisher(fail_count: int):
    """Publisher that returns a slug-conflict 400 for the first `fail_count` calls."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body["fieldData"]["slug"])
        if len(calls) <= fail_count:
            return httpx.Response(400, text="slug already exists")
        return httpx.Response(200, json={"id": "retry-item-id"})

    transport = httpx.MockTransport(handler)
    publisher = WebflowPublisher.__new__(WebflowPublisher)
    publisher._collection_id = "col123"
    publisher._image_field = "cover-image"
    publisher._author_field = "author"
    publisher._category_field = "categories"
    publisher._client = httpx.AsyncClient(
        base_url="https://api.webflow.com/v2",
        transport=transport,
    )
    return publisher, calls


def test_add_draft_retries_with_suffix_on_slug_collision():
    """A 400 'slug already exists' response triggers a retry with a UUID suffix."""
    publisher, calls = _make_slug_collision_publisher(fail_count=1)
    item_id = asyncio.run(publisher.add_draft({"title": "Test Collision"}))
    assert item_id == "retry-item-id"
    assert len(calls) == 2
    base_slug = calls[0]
    retry_slug = calls[1]
    assert retry_slug.startswith(base_slug + "-")
    suffix = retry_slug[len(base_slug) + 1:]
    assert len(suffix) == 8
    assert all(c in "0123456789abcdef" for c in suffix)


def test_add_draft_retries_multiple_times_on_repeated_slug_collision():
    """Repeated slug conflicts each trigger a new UUID retry (up to 5 attempts)."""
    publisher, calls = _make_slug_collision_publisher(fail_count=3)
    item_id = asyncio.run(publisher.add_draft({"title": "Repeated Collision"}))
    assert item_id == "retry-item-id"
    assert len(calls) == 4
    suffixes = [slug.split("-")[-1] for slug in calls[1:]]
    assert len(set(suffixes)) == len(suffixes), "each retry should use a distinct UUID suffix"


def test_make_slug_strips_accented_characters_to_valid_ascii():
    """Accented Latin letters must degrade to ASCII, not survive and break Webflow's slug pattern."""
    slug = _make_slug("Café société: naïve résumé of ML")
    assert _WEBFLOW_SLUG_RE.match(slug)
    assert slug == "cafe-societe-naive-resume-of-ml"


def test_make_slug_falls_back_to_uuid_for_non_latin_title():
    """A title with no ASCII-representable characters must not sanitize to an unstable empty slug."""
    slug = _make_slug("日本語のタイトル")
    assert _WEBFLOW_SLUG_RE.match(slug)
    assert slug.startswith("post-")


def test_add_draft_slug_with_accents_matches_webflow_pattern():
    captured = {}
    publisher = _make_capturing_publisher(captured)
    asyncio.run(publisher.add_draft({"title": "Café société: naïve résumé of ML"}))
    assert _WEBFLOW_SLUG_RE.match(captured["body"]["fieldData"]["slug"])


def test_add_draft_meta_description_word_boundary():
    """seo_description longer than 160 chars must be truncated at a word boundary."""
    captured = {}
    publisher = _make_capturing_publisher(captured)
    long_desc = ("word " * 40).strip()  # 200 chars, all spaces between words
    asyncio.run(publisher.add_draft({"title": "T", "seo_description": long_desc}))
    fd = captured["body"]["fieldData"]
    assert len(fd["short-description"]) <= 160
    assert not fd["short-description"].endswith(" ")
    # must end at a full word, not mid-word
    last_char = fd["short-description"][-1]
    assert last_char not in (" ",), "should not end with trailing space"
