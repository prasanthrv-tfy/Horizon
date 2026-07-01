import json
from pathlib import Path

from .converter import convert_markdown, reading_time


def _strip_leading_h1(markdown: str) -> str:
    """Remove the first H1 line so the Webflow template title isn't duplicated."""
    lines = markdown.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('# '):
            lines.pop(i)
            if i < len(lines) and not lines[i].strip():
                lines.pop(i)
            break
    return '\n'.join(lines)


def load_post(entry: dict, base_dir: Path) -> dict:
    """Read a manifest entry and its paired .md file; return a structured dict for publishing."""
    md_path = base_dir / entry["filename"]
    body = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    html = convert_markdown(_strip_leading_h1(body))
    read_time = reading_time(body)

    published_at = entry.get("published_at", "")
    if published_at and "T" not in published_at:
        # Webflow requires a full ISO 8601 datetime. 9 AM UTC avoids midnight edge-cases
        # while still resolving to "today" in most timezones.
        published_at = f"{published_at}T09:00:00Z"

    return {
        "title": entry.get("title", md_path.stem),
        "markdown": body,
        "html": html,
        "tags": entry.get("tags", []),
        "url": entry.get("url", ""),
        "published_at": published_at,
        "reading_time": read_time,
        "score": float(entry.get("score", 0.0)),
        "dimensions": entry.get("dimensions", {}),
        "inclusion_path": entry.get("inclusion_path", ""),
    }


def load_manifest(manifest_path: Path) -> list[tuple[dict, Path]]:
    """Read a posts.json manifest and return (entry, base_dir) pairs."""
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_dir = manifest_path.parent
    return [(entry, base_dir) for entry in entries]
