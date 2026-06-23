"""Tests for WebflowPublisher.list_authors() and list_categories() — pagination and fail-open."""

import asyncio
import httpx

from src.blog.publisher.webflow import WebflowPublisher, _PAGE_LIMIT


def _make_publisher(handler):
    transport = httpx.MockTransport(handler)
    publisher = WebflowPublisher.__new__(WebflowPublisher)
    publisher._collection_id = "col123"
    publisher._image_field = ""
    publisher._author_field = "author"
    publisher._category_field = "category-2"
    publisher._client = httpx.AsyncClient(
        base_url="https://api.webflow.com/v2",
        transport=transport,
    )
    return publisher


def _items(n: int, prefix: str = "item") -> list:
    return [{"id": f"{prefix}-{i}", "fieldData": {"name": f"Name {i}"}} for i in range(n)]


# ---------------------------------------------------------------------------
# list_authors
# ---------------------------------------------------------------------------

def test_list_authors_single_page():
    items = _items(3, "author")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": items})

    result = asyncio.run(_make_publisher(handler).list_authors("authors-col"))
    assert result == items


def test_list_authors_multi_page():
    page1 = _items(_PAGE_LIMIT, "a")
    page2 = _items(5, "b")
    pages = iter([page1, page2])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": next(pages)})

    result = asyncio.run(_make_publisher(handler).list_authors("authors-col"))
    assert len(result) == _PAGE_LIMIT + 5


def test_list_authors_empty_collection():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": []})

    result = asyncio.run(_make_publisher(handler).list_authors("authors-col"))
    assert result == []


def test_list_authors_http_error_returns_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    result = asyncio.run(_make_publisher(handler).list_authors("authors-col"))
    assert result == []


def test_list_authors_exception_returns_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    result = asyncio.run(_make_publisher(handler).list_authors("authors-col"))
    assert result == []


# ---------------------------------------------------------------------------
# list_categories
# ---------------------------------------------------------------------------

def test_list_categories_single_page():
    items = _items(2, "cat")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": items})

    result = asyncio.run(_make_publisher(handler).list_categories("cats-col"))
    assert result == items


def test_list_categories_multi_page():
    page1 = _items(_PAGE_LIMIT, "c")
    page2 = _items(3, "d")
    pages = iter([page1, page2])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": next(pages)})

    result = asyncio.run(_make_publisher(handler).list_categories("cats-col"))
    assert len(result) == _PAGE_LIMIT + 3


def test_list_categories_empty_collection():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": []})

    result = asyncio.run(_make_publisher(handler).list_categories("cats-col"))
    assert result == []


def test_list_categories_http_error_returns_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden")

    result = asyncio.run(_make_publisher(handler).list_categories("cats-col"))
    assert result == []


def test_list_categories_exception_returns_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("timeout")

    result = asyncio.run(_make_publisher(handler).list_categories("cats-col"))
    assert result == []
