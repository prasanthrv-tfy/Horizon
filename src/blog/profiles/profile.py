from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from src.blog.models import GatePath, ScoringDimension


@dataclass
class BlogPromptProfile:
    """Bundles all prompts needed for one blog generation style."""

    name: str
    blog_system: str
    blog_user: str
    research_system: str
    research_user: str
    # DEPRECATED: replaced by scoring_dimensions + gate_paths. Ignored when scoring_dimensions is set.
    ranking_context: str = ""
    scoring_dimensions: List["ScoringDimension"] = field(default_factory=list)
    gate_paths: List["GatePath"] = field(default_factory=list)
