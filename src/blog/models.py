from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.models import ContentItem


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


class ImageGenerationConfig(BaseModel):
    """Configuration for AI cover image generation during publishing."""

    enabled: bool = False
    model: str = "image-gen/stability.stable-image-core-v1-1"
    base_url_env: str = "TFY_BASE_URL"
    api_key_env: str = "TFY_API_KEY"
    aspect_ratio: str = "16:9"


class PublisherConfig(BaseModel):
    """Configuration for the publishing pipeline."""

    collection_id: str = ""
    site_id: str = ""
    image_field: str = "cover-image"
    authors_collection_id: str = ""
    author_field: str = "author"
    categories_collection_id: str = ""
    category_field: str = "categories"
    publish_mode: str = "draft"  # "draft" | "live"
    deduplication_time_window: int = 14  # days
    max_publish: int = 0  # 0 = publish all
    image_generation: ImageGenerationConfig = ImageGenerationConfig()


class GeneratorConfig(BaseModel):
    """Configuration for the blog generation pipeline."""

    max_posts: int = 4
    profile: str = "engineer"
    topics: List[str] = []
    output_dir: str = "artifacts/blog-posts"
    audience_context: str = ""
    platform_context: str = ""


class BlogConfig(BaseModel):
    """Configuration for the blog module (generator + publisher)."""

    generator: GeneratorConfig = GeneratorConfig()
    publisher: PublisherConfig = PublisherConfig()
