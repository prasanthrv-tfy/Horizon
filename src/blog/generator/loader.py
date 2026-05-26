import json
import re
import sys
from pathlib import Path
from typing import List

from ...models import ContentItem
from ..profiles import PROFILES
from ..profiles.profile import BlogPromptProfile


def _clean_title(title: str) -> str:
    return re.sub(r'^[^\x20-\x7E]+\s*', '', title).strip()


def load_important_items(path: Path) -> List[ContentItem]:
    if not path.exists():
        print(
            f"[error] {path} not found. Run `uv run horizon` first to generate it.",
            file=sys.stderr,
        )
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    if not data:
        print("No items in pipeline output. Nothing to do.", file=sys.stderr)
        sys.exit(0)

    return [ContentItem(**item) for item in data]


def resolve_profiles(name: str) -> List[BlogPromptProfile]:
    """Return the list of profiles to run for the given profile name."""
    if name == "all":
        return list(PROFILES.values())
    if name not in PROFILES:
        available = ", ".join(PROFILES.keys())
        print(
            f"[error] Unknown profile '{name}'. Available profiles: {available}",
            file=sys.stderr,
        )
        sys.exit(1)
    return [PROFILES[name]]
