"""Tests for WebflowPublisher.add_draft() field mapping."""

import asyncio
import json
import httpx

from src.blog.publisher.webflow import WebflowPublisher


def _make_capturing_publisher(captured: dict, image_field="cover-image",
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
    assert "meta-title" in fd
    assert "meta-description" in fd
    assert "description" in fd
    assert "content" in fd
    assert "published-date" in fd
    assert fd["featured-on-top"] is False
    assert fd["latest-news"] is True
    assert fd["main-hero-news"] is False
    assert fd["highlighted-news"] is False
    assert fd["premium-content"] is False
    assert fd["focus-articles"] is False
    # Old field names must not appear
    assert "random" not in fd
    assert "short-description" not in fd
    assert "news-description" not in fd
    assert "date" not in fd


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


def test_add_draft_category_id_injected_as_list():
    captured = {}
    publisher = _make_capturing_publisher(captured)
    asyncio.run(publisher.add_draft({"title": "T", "category_id": "cat-xyz"}))
    assert captured["body"]["fieldData"]["categories"] == ["cat-xyz"]


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
    img = captured["body"]["fieldData"]["cover-image"]
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


def test_add_draft_retries_with_suffix_on_slug_collision():
    """A 400 'slug already exists' response triggers a retry with a hash suffix."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body["fieldData"]["slug"])
        if len(calls) == 1:
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
    item_id = asyncio.run(publisher.add_draft({"title": "Test Collision"}))
    assert item_id == "retry-item-id"
    assert len(calls) == 2
    assert calls[1] == calls[0] + "-" + calls[1].split("-")[-1]  # suffix appended


def test_add_draft_meta_description_word_boundary():
    """seo_description longer than 160 chars must be truncated at a word boundary."""
    captured = {}
    publisher = _make_capturing_publisher(captured)
    long_desc = ("word " * 40).strip()  # 200 chars, all spaces between words
    asyncio.run(publisher.add_draft({"title": "T", "seo_description": long_desc}))
    fd = captured["body"]["fieldData"]
    assert len(fd["meta-description"]) <= 160
    assert not fd["meta-description"].endswith(" ")
    # must end at a full word, not mid-word
    last_char = fd["meta-description"][-1]
    assert last_char not in (" ",), "should not end with trailing space"
