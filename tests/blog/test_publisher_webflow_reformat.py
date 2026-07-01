"""Tests for _reformat_sources() and _normalize_source_item() in webflow.py."""

from src.blog.publisher.webflow import _normalize_source_item, _reformat_sources


# ---------------------------------------------------------------------------
# _normalize_source_item
# ---------------------------------------------------------------------------

def test_normalize_bare_url():
    result = _normalize_source_item("https://example.com/article")
    assert 'href="https://example.com/article"' in result
    assert result.startswith("<li>")
    assert result.endswith("</li>")


def test_normalize_url_with_label_prefix():
    result = _normalize_source_item("Example: https://example.com/article")
    assert result == '<li><a href="https://example.com/article">Example</a></li>'


def test_normalize_anchor_tag_with_label_text():
    raw = '<a href="https://example.com">Example Site</a>'
    result = _normalize_source_item(raw)
    assert result == '<li><a href="https://example.com">Example Site</a></li>'


def test_normalize_anchor_tag_with_prefix_label():
    raw = 'My Source: <a href="https://example.com">https://example.com</a>'
    result = _normalize_source_item(raw)
    assert result == '<li><a href="https://example.com">My Source</a></li>'


def test_normalize_plain_text_no_url():
    result = _normalize_source_item("Just some plain text")
    assert result == "<li>Just some plain text</li>"


# ---------------------------------------------------------------------------
# _reformat_sources
# ---------------------------------------------------------------------------

def test_reformat_sources_normalises_list_items():
    html = (
        "<h2>Sources</h2>"
        "<ul>"
        "<li>https://example.com/a</li>"
        "<li>https://example.com/b</li>"
        "</ul>"
    )
    result = _reformat_sources(html)
    assert "<ul>" in result
    assert "<li>" in result
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
    assert "<ul>" in result


def test_reformat_sources_case_insensitive_heading():
    html = "<h3>sources</h3><ul><li>https://example.com</li></ul>"
    result = _reformat_sources(html)
    assert "<ul>" in result
    assert 'href="https://example.com"' in result


def test_reformat_sources_deduplicates_same_label():
    html = (
        "<h2>Sources</h2><ul>"
        '<li><a href="https://github.com/awslabs/mcp">GitHub</a></li>'
        '<li><a href="https://github.com/BerriAI/litellm">GitHub</a></li>'
        '<li><a href="https://arxiv.org/abs/2507.10789">arXiv</a></li>'
        '<li><a href="https://arxiv.org/html/2507.10789v2">arXiv</a></li>'
        "</ul>"
    )
    result = _reformat_sources(html)
    assert "GitHub (awslabs/mcp)" in result
    assert "GitHub (BerriAI/litellm)" in result
    assert "arXiv (abs/2507.10789)" in result
    assert "arXiv (html/2507.10789v2)" in result
    assert ">GitHub<" not in result  # bare duplicate label must not remain
    assert ">arXiv<" not in result


def test_reformat_sources_unique_labels_unchanged():
    html = (
        "<h2>Sources</h2><ul>"
        '<li><a href="https://aws.amazon.com/blogs/ml/">AWS Blog</a></li>'
        '<li><a href="https://arxiv.org/abs/1234">arXiv</a></li>'
        "</ul>"
    )
    result = _reformat_sources(html)
    assert ">AWS Blog<" in result
    assert ">arXiv<" in result
