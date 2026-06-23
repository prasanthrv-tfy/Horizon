"""Tests for gate-path scoring and relevance ranking in src/blog/generator/scorer.py"""

import asyncio
import json
from datetime import datetime, timezone

import pytest
from rich.console import Console

from src.blog.generator.scorer import rank_by_relevance, score_items_for_profile
from src.blog.models import GatePath, PathDimensionConfig, ScoringDimension
from src.blog.profiles.profile import BlogPromptProfile
from src.models import ContentItem


# --- shared helpers ---


def make_content_item(id="test:rss:1", title="Test Article") -> ContentItem:
    return ContentItem(
        id=id,
        source_type="rss",
        title=title,
        url="https://example.com/article",
        ai_score=7.0,
        ai_tags=["ml"],
        published_at=datetime.now(timezone.utc),
    )


def make_gate_path(name, dims) -> GatePath:
    """dims: list of (dimension_name, weight, threshold)"""
    return GatePath(
        name=name,
        dimensions=[PathDimensionConfig(dimension=d, weight=w, threshold=t) for d, w, t in dims],
    )


def make_profile(gate_paths, dims) -> BlogPromptProfile:
    return BlogPromptProfile(
        name="testprofile",
        blog_system="",
        blog_user="",
        research_system="",
        research_user="",
        scoring_dimensions=dims,
        gate_paths=gate_paths,
    )


class MockAIClient:
    """Minimal AI client stub — returns a fixed JSON string from complete()."""

    def __init__(self, response: str):
        self._response = response
        self.config = None

    async def complete(self, system="", user="", **kwargs) -> str:
        return self._response


_QUIET = Console(quiet=True)


# --- score_items_for_profile ---


def test_score_item_passes_all_gates():
    dim = ScoringDimension(name="quality", description="q", anchors={"1": "low", "10": "high"})
    path = make_gate_path("path_a", [("quality", 1.0, 5.0)])
    profile = make_profile([path], [dim])

    ai_response = json.dumps({"items": [{"dimensions": {"quality": {"score": 8, "reason": "good"}}}]})
    client = MockAIClient(ai_response)
    item = make_content_item()

    scored = asyncio.run(score_items_for_profile([item], client, _QUIET, profile))

    assert len(scored) == 1
    assert scored[0].included is True
    assert scored[0].inclusion_path == "path_a"


def test_score_item_fails_threshold():
    dim = ScoringDimension(name="quality", description="q", anchors={"1": "low", "10": "high"})
    path = make_gate_path("path_a", [("quality", 1.0, 7.0)])
    profile = make_profile([path], [dim])

    ai_response = json.dumps({"items": [{"dimensions": {"quality": {"score": 4, "reason": "weak"}}}]})
    client = MockAIClient(ai_response)

    scored = asyncio.run(score_items_for_profile([make_content_item()], client, _QUIET, profile))

    assert scored[0].included is False
    assert "quality" in scored[0].failed_gates.get("path_a", [])


def test_score_item_fails_path_a_passes_path_b():
    dim_a = ScoringDimension(name="research", description="r", anchors={"1": "low", "10": "high"})
    dim_b = ScoringDimension(name="applicability", description="a", anchors={"1": "low", "10": "high"})
    path_a = make_gate_path("path_a", [("research", 1.0, 8.0)])
    path_b = make_gate_path("path_b", [("applicability", 1.0, 5.0)])
    profile = make_profile([path_a, path_b], [dim_a, dim_b])

    # research=5 (fails path_a gate of 8), applicability=7 (passes path_b gate of 5)
    ai_response = json.dumps({"items": [{"dimensions": {
        "research": {"score": 5, "reason": "ok"},
        "applicability": {"score": 7, "reason": "good"},
    }}]})
    client = MockAIClient(ai_response)

    scored = asyncio.run(score_items_for_profile([make_content_item()], client, _QUIET, profile))

    assert scored[0].included is True
    assert scored[0].inclusion_path == "path_b"


def test_score_item_ai_empty_response_excludes_gracefully():
    dim = ScoringDimension(name="quality", description="q", anchors={"1": "low", "10": "high"})
    path = make_gate_path("path_a", [("quality", 1.0, 5.0)])
    profile = make_profile([path], [dim])

    client = MockAIClient("")  # empty response → parse_json_response returns None

    scored = asyncio.run(score_items_for_profile([make_content_item()], client, _QUIET, profile))

    assert scored[0].included is False
    assert scored[0].dimension_scores == {}


def test_score_weighted_sum_uses_winning_path_weights():
    dim_a = ScoringDimension(name="research", description="r", anchors={"1": "low", "10": "high"})
    dim_b = ScoringDimension(name="applicability", description="a", anchors={"1": "low", "10": "high"})
    # path_a: research weight=1.0; path_b: applicability weight=0.5
    path_a = make_gate_path("path_a", [("research", 1.0, 5.0), ("applicability", 0.0, 0.0)])
    path_b = make_gate_path("path_b", [("research", 0.0, 0.0), ("applicability", 0.5, 5.0)])
    profile = make_profile([path_a, path_b], [dim_a, dim_b])

    ai_response = json.dumps({"items": [{"dimensions": {
        "research": {"score": 8, "reason": "good"},
        "applicability": {"score": 6, "reason": "ok"},
    }}]})
    client = MockAIClient(ai_response)

    scored = asyncio.run(score_items_for_profile([make_content_item()], client, _QUIET, profile))

    si = scored[0]
    assert si.included is True
    assert si.inclusion_path == "path_a"
    # path_a: research*1.0 + applicability*0.0 = 8.0
    assert abs(si.weighted_sum - 8.0) < 0.01


# --- rank_by_relevance ---


def test_rank_by_relevance_reorders_items():
    items = [make_content_item("id:rss:1", "First"), make_content_item("id:rss:2", "Second")]
    # AI says second item should come first
    response = json.dumps({"ranked_ids": ["id:rss:2", "id:rss:1"]})
    client = MockAIClient(response)

    ranked = asyncio.run(rank_by_relevance(items, client, _QUIET))

    assert ranked[0].id == "id:rss:2"
    assert ranked[1].id == "id:rss:1"


def test_rank_by_relevance_handles_unknown_ids():
    items = [make_content_item("id:rss:1", "First"), make_content_item("id:rss:2", "Second")]
    # Response includes one unknown id — should be ignored, known items preserved
    response = json.dumps({"ranked_ids": ["id:rss:unknown", "id:rss:1", "id:rss:2"]})
    client = MockAIClient(response)

    ranked = asyncio.run(rank_by_relevance(items, client, _QUIET))

    assert {r.id for r in ranked} == {"id:rss:1", "id:rss:2"}


def test_rank_by_relevance_returns_original_on_ai_failure():
    items = [make_content_item("id:rss:1"), make_content_item("id:rss:2")]

    class FailingClient:
        config = None
        async def complete(self, **kwargs):
            raise RuntimeError("network error")

    ranked = asyncio.run(rank_by_relevance(items, FailingClient(), _QUIET))

    assert [r.id for r in ranked] == ["id:rss:1", "id:rss:2"]


def test_rank_by_relevance_single_item_no_ai_call():
    item = make_content_item()
    call_count = 0

    class TrackingClient:
        config = None
        async def complete(self, **kwargs):
            nonlocal call_count
            call_count += 1
            return ""

    result = asyncio.run(rank_by_relevance([item], TrackingClient(), _QUIET))

    assert result == [item]
    assert call_count == 0
