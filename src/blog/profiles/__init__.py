from . import news, engineer
from .profile import BlogPromptProfile

PROFILES: dict[str, BlogPromptProfile] = {
    p.name: p for p in [news.PROFILE, engineer.PROFILE]
}

__all__ = ["PROFILES", "BlogPromptProfile"]
