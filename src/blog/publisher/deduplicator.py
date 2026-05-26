import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def normalise_title(title: str) -> str:
    """Lowercase, strip, collapse whitespace, remove punctuation."""
    title = title.lower().strip()
    title = re.sub(r"[^\w\s]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def deduplicate_posts(
    posts: List[Tuple[dict, Path]],
    webflow_items: List[Dict[str, Any]],
) -> Tuple[List[Tuple[dict, Path]], List[Tuple[dict, Path]]]:
    """Return (kept, skipped) — skipped posts have a title already in webflow_items."""
    existing = {
        normalise_title(item.get("fieldData", {}).get("name", ""))
        for item in webflow_items
        if item.get("fieldData", {}).get("name")
    }

    kept: List[Tuple[dict, Path]] = []
    skipped: List[Tuple[dict, Path]] = []
    for entry, base_dir in posts:
        title = entry.get("title", "")
        if normalise_title(title) in existing:
            skipped.append((entry, base_dir))
        else:
            kept.append((entry, base_dir))
    return kept, skipped
