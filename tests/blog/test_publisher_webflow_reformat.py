"""Tests for _reformat_sources() and _normalize_source_item() in webflow.py."""

from src.blog.publisher.webflow import _normalize_source_item, _reformat_sources


# ---------------------------------------------------------------------------
# _normalize_source_item
# ---------------------------------------------------------------------------

def test_normalize_bare_url():
    result = _normalize_source_item("https://example.com/article")
    assert 'href="https://example.com/article"' in result
    assert result.startswith("<p>")
    assert result.endswith("</p>")


def test_normalize_url_with_label_prefix():
    result = _normalize_source_item("Example: https://example.com/article")
    assert "Example:" in result
    assert 'href="https://example.com/article"' in result


def test_normalize_anchor_tag_with_label_text():
    raw = '<a href="https://example.com">Example Site</a>'
    result = _normalize_source_item(raw)
    assert 'href="https://example.com"' in result
    assert "Example Site" in result


def test_normalize_anchor_tag_with_prefix_label():
    raw = 'My Source: <a href="https://example.com">https://example.com</a>'
    result = _normalize_source_item(raw)
    assert "My Source:" in result
    assert 'href="https://example.com"' in result


def test_normalize_plain_text_no_url():
    result = _normalize_source_item("Just some plain text")
    assert result == "<p>Just some plain text</p>"


# ---------------------------------------------------------------------------
# _reformat_sources
# ---------------------------------------------------------------------------

def test_reformat_sources_converts_ul_to_paragraphs():
    html = (
        "<h2>Sources</h2>"
        "<ul>"
        "<li>https://example.com/a</li>"
        "<li>https://example.com/b</li>"
        "</ul>"
    )
    result = _reformat_sources(html)
    assert "<ul>" not in result
    assert "<li>" not in result
    assert 'href="https://example.com/a"' in result
    assert 'href="https://example.com/b"' in result


def test_reformat_sources_no_sources_block_unchanged():
    html = "<p>This has no sources section.</p>"
    result = _reformat_sources(html)
    assert result == html


def test_reformat_sources_preserves_content_before_sources():
    html = "<p>Intro content</p><h2>Sources</h2><ul><li>https://example.com</li></ul>"
    result = _reformat_sources(html)
    assert "<p>Intro content</p>" in result
    assert "<ul>" not in result


def test_reformat_sources_case_insensitive_heading():
    html = "<h3>sources</h3><ul><li>https://example.com</li></ul>"
    result = _reformat_sources(html)
    assert "<ul>" not in result
    assert 'href="https://example.com"' in result
