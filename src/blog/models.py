from dataclasses import dataclass, field
from typing import List

from pydantic import BaseModel


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
    output_dir: str = "data/blog-posts"
    prompt_profile: str = "journalist"
    audience_context: str = ""
    platform_context: str = ""
