"""Tests for pure functions and file I/O in src/blog/generator/"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.blog.generator.fetcher import _strip_html
from src.blog.generator.loader import _clean_title, load_important_items, resolve_profiles
from src.blog.generator.reporter import _write_ranking_results, _write_run_log
from src.blog.generator.scorer import _compute_weighted_sum
from src.blog.generator.writer import BlogWriter
from src.blog.models import GatePath, PathDimensionConfig, ScoredItem, ScoringDimension
from src.blog.profiles.profile import BlogPromptProfile
from src.models import ContentItem


# --- shared helpers ---


def make_content_item(
    id="test:rss:1",
    title="Test Article",
    content=None,
    ai_tags=None,
    ai_score=7.0,
) -> ContentItem:
    return ContentItem(
        id=id,
        source_type="rss",
        title=title,
        url="https://example.com/article",
        content=content,
        ai_score=ai_score,
        ai_tags=ai_tags or [],
        published_at=datetime.now(timezone.utc),
    )


def make_gate_path(name, dims) -> GatePath:
    """dims: list of (dimension_name, weight, threshold)"""
    return GatePath(
        name=name,
        dimensions=[PathDimensionConfig(dimension=d, weight=w, threshold=t) for d, w, t in dims],
    )


def make_scored_item(included=True) -> ScoredItem:
    item = make_content_item()
    return ScoredItem(
        item=item,
        dimension_scores={"quality": {"score": 8, "reason": "good"}},
        path_results={"path_a": {"passed": included, "scores": {"quality": 8}, "failed_gates": []}},
        included=included,
        inclusion_path="path_a" if included else None,
        failed_gates={} if included else {"path_a": ["quality"]},
        weighted_sum=8.0 if included else 0.0,
    )


def make_minimal_profile(name="testprofile") -> BlogPromptProfile:
    dim = ScoringDimension(name="quality", description="quality", anchors={"1": "low", "10": "high"})
    path = make_gate_path("path_a", [("quality", 1.0, 5.0)])
    return BlogPromptProfile(
        name=name,
        blog_system="",
        blog_user="",
        research_system="",
        research_user="",
        scoring_dimensions=[dim],
        gate_paths=[path],
    )


# --- _clean_title ---


def test_clean_title_strips_emoji_prefix():
    assert _clean_title("🚀 New Release") == "New Release"


def test_clean_title_strips_multiple_emojis():
    assert _clean_title("🔥💡 Breaking News") == "Breaking News"


def test_clean_title_ascii_unchanged():
    assert _clean_title("GPT-5 Announced") == "GPT-5 Announced"


def test_clean_title_empty():
    assert _clean_title("") == ""


def test_clean_title_mixed_emoji_and_text():
    assert _clean_title("🧪 Test: Mixed content") == "Test: Mixed content"


# --- _strip_html ---


def test_strip_html_extracts_paragraph_text():
    assert "Hello world" in _strip_html("<p>Hello world</p>")


def test_strip_html_removes_script_content():
    result = _strip_html("<p>visible</p><script>alert('xss')</script>")
    assert "visible" in result
    assert "alert" not in result


def test_strip_html_removes_style_content():
    result = _strip_html("<style>body { color: red; }</style><p>text</p>")
    assert "color" not in result
    assert "text" in result


def test_strip_html_plain_text_passthrough():
    assert "just plain text" in _strip_html("just plain text")


# --- _compute_weighted_sum ---


def test_compute_weighted_sum_correct_total():
    path = make_gate_path("A", [("quality", 0.6, 5.0), ("relevance", 0.4, 5.0)])
    scores = {"quality": {"score": 8}, "relevance": {"score": 6}}
    result = _compute_weighted_sum(scores, path)
    assert abs(result - (0.6 * 8 + 0.4 * 6)) < 0.001


def test_compute_weighted_sum_zero_weight_ignored():
    path = make_gate_path("A", [("quality", 1.0, 5.0), ("ignored", 0.0, 5.0)])
    scores = {"quality": {"score": 8}, "ignored": {"score": 10}}
    result = _compute_weighted_sum(scores, path)
    assert abs(result - 8.0) < 0.001


def test_compute_weighted_sum_missing_score_is_zero():
    path = make_gate_path("A", [("quality", 1.0, 5.0)])
    assert _compute_weighted_sum({}, path) == 0.0


# --- load_important_items ---


def test_load_important_items_valid_json(tmp_path):
    data = [{"id": "rss:news:1", "source_type": "rss", "title": "Test", "url": "https://example.com", "published_at": "2026-01-01T00:00:00Z"}]
    p = tmp_path / "items.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    items = load_important_items(p)
    assert len(items) == 1
    assert items[0].title == "Test"


def test_load_important_items_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit):
        load_important_items(tmp_path / "nonexistent.json")


def test_load_important_items_empty_array_exits(tmp_path):
    p = tmp_path / "items.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_important_items(p)


# --- resolve_profiles ---


def test_resolve_profiles_known_name():
    profiles = resolve_profiles("news")
    assert len(profiles) == 1
    assert profiles[0].name == "news"


def test_resolve_profiles_all_returns_multiple():
    profiles = resolve_profiles("all")
    assert len(profiles) >= 2


def test_resolve_profiles_unknown_exits():
    with pytest.raises(SystemExit):
        resolve_profiles("nonexistent_profile_xyz")


# --- _write_run_log ---


def test_write_run_log_creates_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log_path = _write_run_log([make_scored_item(True), make_scored_item(False)], "news")
    assert Path(log_path).exists()


def test_write_run_log_json_structure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log_path = _write_run_log([make_scored_item(True), make_scored_item(False)], "news")
    data = json.loads(Path(log_path).read_text())
    assert data["profile"] == "news"
    assert data["items_evaluated"] == 2
    assert data["items_included"] == 1
    assert data["items_excluded"] == 1
    assert "results" in data


# --- _write_ranking_results ---


def test_write_ranking_results_creates_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    profile = make_minimal_profile()
    _write_ranking_results({"testprofile": (profile, [make_scored_item()])}, 1, 4)
    assert (tmp_path / "artifacts" / "ranking_results.md").exists()


def test_write_ranking_results_contains_profile_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    profile = make_minimal_profile()
    _write_ranking_results({"testprofile": (profile, [make_scored_item()])}, 1, 4)
    content = (tmp_path / "artifacts" / "ranking_results.md").read_text()
    assert "testprofile" in content
