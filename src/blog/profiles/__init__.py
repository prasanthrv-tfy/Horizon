from . import journalist, practitioner
from .profile import BlogPromptProfile

PROFILES: dict[str, BlogPromptProfile] = {
    p.name: p for p in [journalist.PROFILE, practitioner.PROFILE]
}

__all__ = ["PROFILES", "BlogPromptProfile"]
