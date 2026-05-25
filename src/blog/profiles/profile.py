from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..models import ScoringDimension


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
    # Each path is a list of dimension names; item included if ANY path has ALL dims >= threshold.
    gate_paths: List[List[str]] = field(default_factory=list)
