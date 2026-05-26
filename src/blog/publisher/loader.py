import re
from pathlib import Path
from typing import Any, Dict

from .converter import convert_markdown, reading_time

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FIELD_RE = re.compile(r'^(\w[\w-]*):\s*"?([^"\n]*)"?\s*$', re.MULTILINE)
_TAGS_RE = re.compile(r"^tags:\s*\[([^\]]*)\]", re.MULTILINE)
_DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+?)(?:-\w{2})?$")


def _parse_front_matter(text: str) -> tuple[dict, str]:
    """Return (fields dict, body text). Fields are empty if no front matter found."""
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    fm_block = m.group(1)
    body = text[m.end():]
    fields: Dict[str, Any] = {}
    for key, val in _FIELD_RE.findall(fm_block):
        fields[key] = val.strip()
    # tags are a special case: `tags: [a, b, c]`
    tags_m = _TAGS_RE.search(fm_block)
    if tags_m:
        fields["tags"] = [t.strip() for t in tags_m.group(1).split(",") if t.strip()]
    return fields, body


def load_post(path: Path) -> dict:
    """Read a generated Jekyll post file and return a structured dict."""
    text = path.read_text(encoding="utf-8")
    fields, body = _parse_front_matter(text)

    # Derive fallback values from filename: YYYY-MM-DD-<slug>-<lang>.md
    stem = path.stem
    date_fallback = ""
    slug_fallback = stem
    dm = _DATE_PREFIX_RE.match(stem)
    if dm:
        date_fallback = dm.group(1)
        slug_fallback = dm.group(2)

    title = fields.get("title", slug_fallback)
    slug = fields.get("slug", slug_fallback)
    published_at = fields.get("date", date_fallback)
    url = fields.get("original_url", "")
    tags = fields.get("tags", [])

    raw_score = fields.get("score", "")
    try:
        score = float(raw_score)
    except (ValueError, TypeError):
        score = 0.0

    html = convert_markdown(body)
    read_time = reading_time(body)

    return {
        "title": title,
        "slug": slug,
        "markdown": body,
        "html": html,
        "tags": tags,
        "url": url,
        "published_at": f"{published_at}T09:00:00Z" if published_at and "T" not in published_at else published_at,
        "reading_time": read_time,
        "score": score,
    }
