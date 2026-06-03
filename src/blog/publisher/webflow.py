import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_SOURCES_RE = re.compile(
    r'(<h[2-4][^>]*>[Ss]ources</h[2-4]>)\s*<ul>(.*?)</ul>',
    re.DOTALL,
)


def _reformat_sources(html: str) -> str:
    """Convert the Sources <ul>/<li> block to <p> elements.

    Webflow's Rich Text API sanitizer strips <li> whose only content is an <a>
    element, which is the exact pattern every Sources section uses. Converting
    to <p> tags preserves the links.
    """
    def _replace(m: re.Match) -> str:
        heading = m.group(1)
        items = re.findall(r'<li>(.*?)</li>', m.group(2), re.DOTALL)
        paragraphs = ''.join(f'<p>{item.strip()}</p>' for item in items)
        return heading + paragraphs
    return _SOURCES_RE.sub(_replace, html)

import httpx

from .publisher import Publisher

WEBFLOW_API_BASE = "https://api.webflow.com/v2"
_PAGE_LIMIT = 100

logger = logging.getLogger(__name__)


def _truncate_title(title: str, max_length: int = 60) -> str:
    if len(title) <= max_length:
        return title
    truncated = title[:max_length]
    boundary = truncated.rfind(' ')
    return (truncated[:boundary] if boundary > 0 else truncated).strip()


def _make_slug(title: str, max_length: int = 60) -> str:
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    if len(slug) > max_length:
        truncated = slug[:max_length]
        boundary = truncated.rfind('-')
        slug = truncated[:boundary] if boundary > 0 else truncated
    return slug


class WebflowPublisher(Publisher):
    """Webflow CMS implementation of Publisher (Staged Items API)."""

    def __init__(self, token: str, collection_id: str) -> None:
        self._collection_id = collection_id
        self._client = httpx.AsyncClient(
            base_url=WEBFLOW_API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "accept": "application/json",
                "content-type": "application/json",
            },
        )

    async def add_draft(self, item: dict) -> str:
        """Create a draft CMS item and return the Webflow-assigned item ID."""
        title = _truncate_title(item.get("title", ""))
        slug = _make_slug(item.get("title", ""))
        payload = {
            "fieldData": {
                "name": title,
                "slug": slug,
                "meta-title": item.get("seo_title", title)[:60],
                "meta-description": item.get("seo_description", "")[:160],
                "content": _reformat_sources(item.get("html", "")),
                "published-date": item.get("published_at", ""),
                "min-read": item.get("reading_time", "1 min read"),
                "featured-on-top": "false",
            },
            "isArchived": False,
            "isDraft": True,
        }
        resp = await self._client.post(
            f"/collections/{self._collection_id}/items",
            json=payload,
        )
        if not resp.is_success:
            raise RuntimeError(
                f"Webflow add_draft failed: HTTP {resp.status_code} — {resp.text}"
            )
        return str(resp.json().get("id", ""))

    async def list_items(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Fetch all collection items, optionally filtered to those on or after `since`."""
        all_items: List[Dict[str, Any]] = []
        offset = 0

        while True:
            resp = await self._client.get(
                f"/collections/{self._collection_id}/items",
                params={"limit": _PAGE_LIMIT, "offset": offset},
            )
            if resp.status_code == 429:
                raise RuntimeError(
                    "Webflow API rate limit exceeded (HTTP 429). "
                    "Wait before retrying."
                )
            resp.raise_for_status()

            data = resp.json()
            items = data.get("items", [])
            if not items:
                break

            for item in items:
                field_name = item.get("fieldData", {}).get("name")
                if field_name is None:
                    logger.warning("Webflow item %s is missing fieldData.name", item.get("id"))

            if since is not None:
                items = [i for i in items if _item_is_after(i, since)]

            all_items.extend(items)
            offset += len(data.get("items", []))

            if len(data.get("items", [])) < _PAGE_LIMIT:
                break

        return all_items

    async def get_item(self, item_id: str) -> Dict[str, Any]:
        """Retrieve a single item by its Webflow ID."""
        resp = await self._client.get(
            f"/collections/{self._collection_id}/items/{item_id}"
        )
        if not resp.is_success:
            raise RuntimeError(
                f"Webflow API error fetching item {item_id}: HTTP {resp.status_code}"
            )
        return resp.json()

    async def publish_draft(self, item_id: str) -> None:
        """Promote a staged draft item to live."""
        resp = await self._client.post(
            f"/collections/{self._collection_id}/items/publish",
            json={"itemIds": [item_id]},
        )
        if not resp.is_success:
            raise RuntimeError(
                f"Webflow publish_draft failed: HTTP {resp.status_code} — {resp.text}"
            )
        data = resp.json()
        published = data.get("publishedItemIds", [])
        errors = data.get("errors", [])
        if item_id not in published or item_id in errors:
            raise RuntimeError(
                f"Webflow publish_draft failed for item {item_id}: "
                f"publishedItemIds={published}, errors={errors}"
            )

    async def delete_item(self, item_id: str) -> None:
        """Remove an item from the collection."""
        resp = await self._client.request(
            "DELETE",
            f"/collections/{self._collection_id}/items",
            json={"items": [{"id": item_id}]},
        )
        resp.raise_for_status()

    async def aclose(self) -> None:
        await self._client.aclose()


def _parse_iso(raw: str) -> Optional[datetime]:
    """Parse an ISO 8601 string to datetime, returning None on failure."""
    try:
        # Python 3.11+ handles Z suffix; strip it for older versions
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _item_is_after(item: Dict[str, Any], since: datetime) -> bool:
    """Return True if the item's lastPublished or createdOn is on or after `since`."""
    since_utc = since.replace(tzinfo=timezone.utc) if since.tzinfo is None else since
    for key in ("lastPublished", "createdOn"):
        raw: Any = item.get(key)
        if raw and isinstance(raw, str):
            dt = _parse_iso(raw)
            if dt is not None:
                dt_utc = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
                return dt_utc >= since_utc
    return True  # include items with no date rather than silently drop them
