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
    anchors: Dict[str, str]  # e.g. {"1": "no ML content", "5": "incremental", "10": "paradigm shift"}


@dataclass
class PathDimensionConfig:
    """Configures how one dimension is used within a specific gate path."""

    dimension: str   # must match a ScoringDimension.name in the profile
    weight: float
    threshold: float


@dataclass
class GatePath:
    """A named gate path that owns its dimension configs (thresholds and weights)."""

    name: str
    dimensions: List[PathDimensionConfig] = field(default_factory=list)


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
    markdown: str
    language: str
    score: float
    url: str
    tags: List[str] = field(default_factory=list)
    published_at: str = ""


class PublisherConfig(BaseModel):
    """Configuration for the publishing pipeline."""

    collection_id: str = ""
    deduplication_time_window: int = 14  # days


class BlogConfig(BaseModel):
    """Configuration for blog post generation."""

    max_posts: int = 4
    topics: List[str] = []
    output_dir: str = "artifacts/blog-posts"
    prompt_profile: str = "engineer"
    audience_context: str = ""
    platform_context: str = ""
    publisher: PublisherConfig = PublisherConfig()
