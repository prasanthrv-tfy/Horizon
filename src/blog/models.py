from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel

if TYPE_CHECKING:
    from ..models import ContentItem


@dataclass
class ScoringDimension:
    """A named scoring axis used to evaluate content items for a blog profile."""

    name: str
    description: str
    gate_threshold: float
    path_a_weight: float
    path_b_weight: float
    anchors: Dict[str, str]  # e.g. {"1": "no ML content", "5": "incremental", "10": "paradigm shift"}
    path_thresholds: Dict[str, float] = field(default_factory=dict)  # e.g. {"A": 7.0} overrides gate_threshold per path


@dataclass
class ScoredItem:
    """An item with multi-dimensional scores, gate results, and inclusion decision."""

    item: ContentItem
    dimension_scores: Dict[str, Dict[str, Any]]  # dim_name -> {score, reason}
    path_results: Dict[str, Dict[str, Any]]       # path_label -> {passed, scores, failed_gates}
    included: bool
    inclusion_path: Optional[str]                 # "A", "B", etc. — None if excluded
    failed_gates: Dict[str, List[str]]            # path_label -> [dim names that failed]
    weighted_sum: float


@dataclass
class BlogPost:
    """A generated blog post for a single content item."""

    item_id: str
    title: str
    slug: str
    markdown: str
    language: str
    score: float
    url: str
    tags: List[str] = field(default_factory=list)
    published_at: str = ""


class BlogConfig(BaseModel):
    """Configuration for blog post generation."""

    max_posts: int = 4
    topics: List[str] = []
    output_dir: str = "artifacts/blog-posts"
    prompt_profile: str = "practitioner"
    audience_context: str = ""
    platform_context: str = ""
