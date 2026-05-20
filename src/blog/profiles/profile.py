from dataclasses import dataclass


@dataclass
class BlogPromptProfile:
    """Bundles all prompts needed for one blog generation style."""

    name: str
    blog_system: str
    blog_user: str
    research_system: str
    research_user: str
