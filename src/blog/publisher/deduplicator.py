import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def normalise_title(title: str) -> str:
    """Lowercase, strip, collapse whitespace, remove punctuation."""
    title = title.lower().strip()
    title = re.sub(r"[^\w\s]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def _extract_title(post_path: Path) -> str:
    """Read the post's front matter title field; fall back to filename stem."""
    try:
        content = post_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("title:"):
                raw = line[len("title:"):].strip().strip('"').strip("'")
                if raw:
                    return raw
    except OSError:
        pass
    return post_path.stem


def deduplicate_posts(
    posts: List[Path],
    webflow_items: List[Dict[str, Any]],
) -> Tuple[List[Path], List[Path]]:
    """Return (kept, skipped) — skipped posts have a title already in webflow_items."""
    existing = {
        normalise_title(item.get("fieldData", {}).get("name", ""))
        for item in webflow_items
        if item.get("fieldData", {}).get("name")
    }

    kept: List[Path] = []
    skipped: List[Path] = []
    for post in posts:
        title = _extract_title(post)
        if normalise_title(title) in existing:
            skipped.append(post)
        else:
            kept.append(post)
    return kept, skipped
