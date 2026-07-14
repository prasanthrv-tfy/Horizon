import logging
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

_SOURCES_RE = re.compile(
    r'(<h[2-4][^>]*>[Ss]ources</h[2-4]>)\s*<ul>(.*?)</ul>',
    re.DOTALL,
)
_ANCHOR_TAG_RE = re.compile(r'<a href="([^"]+)">(.*?)</a>', re.DOTALL)
_BARE_URL_RE = re.compile(r'https?://[^\s<>"\']+')
_LIST_TAG_RE = re.compile(r'<(ol|ul)(\s[^>]*)?>', re.IGNORECASE)


def _domain(url: str) -> str:
    return urlparse(url).netloc.lstrip('www.')


def _normalize_source_item(raw: str) -> str:
    """Normalise any source item to '<li><a href="url">label</a></li>'.

    Handles all AI output patterns: bare URL, markdown link with label,
    label+bare-URL, label+markdown-link, and label+url-as-link-text.
    """
    raw = raw.strip()
    a_match = _ANCHOR_TAG_RE.search(raw)
    if a_match:
        url = a_match.group(1)
        link_text = a_match.group(2).strip()
        prefix = raw[:a_match.start()].strip().rstrip(':').strip()
        if prefix:
            label = prefix
        elif not link_text.startswith('http'):
            label = link_text
        else:
            label = _domain(url)
        return f'<li><a href="{url}">{label}</a></li>'
    # No <a> — bare URL text (converter._URL_RE skips URLs preceded by >)
    url_match = _BARE_URL_RE.search(raw)
    if url_match:
        url = url_match.group(0)
        prefix = raw[:url_match.start()].strip().rstrip(':').strip()
        label = prefix if prefix else _domain(url)
        return f'<li><a href="{url}">{label}</a></li>'
    return f'<li>{raw}</li>'


def _style_lists(html: str) -> str:
    """Inject inline styles into <ol> and <ul> so Webflow renders them correctly.

    Webflow's CMS API accepts raw HTML but does not apply page-level CSS to
    injected list elements, causing them to render without indentation or markers.
    """
    def _replace(m: re.Match) -> str:
        tag = m.group(1).lower()
        existing_attrs = m.group(2) or ""
        list_style = "decimal" if tag == "ol" else "disc"
        return f'<{tag}{existing_attrs} style="list-style-type:{list_style};padding-left:1.5em;">'
    return _LIST_TAG_RE.sub(_replace, html)


def _deduplicate_source_labels(items: list) -> list:
    """Append URL path context to source labels that appear more than once.

    e.g. three items labeled 'GitHub' become 'GitHub (awslabs/mcp)',
    'GitHub (a2aproject/a2a-go)', 'GitHub (BerriAI/litellm)'.
    Works for any domain: 'AWS Blog', 'arXiv', etc.
    """
    from collections import Counter
    parsed = []
    for item in items:
        a_match = _ANCHOR_TAG_RE.search(item)
        if a_match:
            parsed.append((a_match.group(2).strip(), a_match.group(1), True))
        else:
            parsed.append((item, "", False))

    label_counts = Counter(label for label, _, has_link in parsed if has_link)

    result = []
    for label, url, has_link in parsed:
        if has_link and label_counts[label] > 1:
            parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
            qualifier = "/".join(parts[:2])
            new_label = f"{label} ({qualifier})" if qualifier else label
            result.append(f'<li><a href="{url}">{new_label}</a></li>')
        elif has_link:
            result.append(f'<li><a href="{url}">{label}</a></li>')
        else:
            result.append(item)
    return result


def _reformat_sources(html: str) -> str:
    """Normalise the Sources <ul>/<li> block so each item is '<li><a href="url">Label</a></li>'.

    Also deduplicates labels that share the same text by appending URL path context,
    e.g. two 'GitHub' items become 'GitHub (awslabs/mcp)' and 'GitHub (BerriAI/litellm)'.
    """
    def _replace(m: re.Match) -> str:
        heading = m.group(1)
        raw_items = re.findall(r'<li>(.*?)</li>', m.group(2), re.DOTALL)
        normalized = [_normalize_source_item(item) for item in raw_items]
        normalized = _deduplicate_source_labels(normalized)
        return heading + '<ul>' + ''.join(normalized) + '</ul>'
    return _SOURCES_RE.sub(_replace, html)

import asyncio
import hashlib
import uuid

import httpx

from .publisher import Publisher

_RETRYABLE_UPLOAD_ERRORS = (
    httpx.WriteTimeout,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.TransportError,
)

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
    slug = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
    slug = slug.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    if len(slug) > max_length:
        truncated = slug[:max_length]
        boundary = truncated.rfind('-')
        slug = truncated[:boundary] if boundary > 0 else truncated
    if not slug:
        slug = f"post-{uuid.uuid4().hex[:8]}"
    return slug


class WebflowPublisher(Publisher):
    """Webflow CMS implementation of Publisher (Staged Items API)."""

    def __init__(self, token: str, collection_id: str, image_field: str = "thumbnail-image", author_field: str = "author", category_field: str = "categories", image_upload_timeout: float = 120.0) -> None:
        self._collection_id = collection_id
        self._image_field = image_field
        self._author_field = author_field
        self._category_field = category_field
        self._image_upload_timeout = image_upload_timeout
        self._client = httpx.AsyncClient(
            base_url=WEBFLOW_API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "accept": "application/json",
                "content-type": "application/json",
            },
            timeout=httpx.Timeout(30.0),
        )

    async def upload_asset(
        self, image_bytes: bytes, filename: str, site_id: str
    ) -> Optional[Dict[str, Any]]:
        """Upload image bytes to Webflow Assets via the two-step presigned S3 flow.

        Retries up to 3 times with exponential backoff on transient network errors.
        Returns {"id": asset_id, "hostedUrl": url} or None on failure.
        """
        for attempt in range(3):
            result = await self._try_upload_asset(image_bytes, filename, site_id)
            if result is not None:
                return result
            if attempt < 2:
                wait_seconds = 2 ** (attempt + 1)  # 2s, 4s
                logger.warning(
                    "Asset upload attempt %d/3 failed — retrying in %ds",
                    attempt + 1,
                    wait_seconds,
                )
                await asyncio.sleep(wait_seconds)
        logger.warning("Asset upload failed after 3 attempts — post will publish without image")
        return None

    async def _try_upload_asset(
        self, image_bytes: bytes, filename: str, site_id: str
    ) -> Optional[Dict[str, Any]]:
        file_hash = hashlib.md5(image_bytes).hexdigest()
        # Step 1: register the asset with Webflow and get the presigned S3 upload URL
        try:
            logger.debug("Webflow asset step 1: POST /sites/%s/assets (file=%s, hash=%s)", site_id, filename, file_hash)
            resp = await self._client.post(
                f"/sites/{site_id}/assets",
                json={"fileName": filename, "fileHash": file_hash},
            )
            if not resp.is_success:
                logger.warning(
                    "Webflow asset step 1 failed: HTTP %s — %s",
                    resp.status_code,
                    resp.text,
                )
                return None
        except Exception as exc:
            logger.warning("Webflow asset step 1 (metadata POST) raised: %s", exc, exc_info=True)
            return None

        data = resp.json()
        upload_url = data.get("uploadUrl")
        upload_details = data.get("uploadDetails", {})
        asset_id = data.get("id", "")
        hosted_url = data.get("hostedUrl", "")

        if not upload_url:
            logger.warning("Webflow asset step 1 response missing uploadUrl — full response: %s", data)
            return None

        # Step 2: POST multipart to the presigned S3 URL using a plain httpx client (no auth headers)
        s3_timeout = httpx.Timeout(connect=10.0, write=self._image_upload_timeout, read=60.0, pool=10.0)
        try:
            logger.debug(
                "Webflow asset step 2: POST %s (fields=%s)",
                upload_url,
                list(upload_details.keys()),
            )
            form_data = {key: (None, str(value)) for key, value in upload_details.items()}
            form_data["file"] = (filename, image_bytes, "image/png")
            async with httpx.AsyncClient(timeout=s3_timeout) as s3_client:
                s3_resp = await s3_client.post(upload_url, files=form_data)
            if not s3_resp.is_success:
                logger.warning(
                    "Webflow asset step 2 (S3 upload) failed: HTTP %s — %s",
                    s3_resp.status_code,
                    s3_resp.text[:500],
                )
                return None
        except _RETRYABLE_UPLOAD_ERRORS as exc:
            logger.warning(
                "Webflow asset step 2 (S3 upload to %s) raised retryable error: %s",
                upload_url,
                exc,
            )
            return None
        except Exception as exc:
            logger.warning(
                "Webflow asset step 2 (S3 upload to %s) raised: %s",
                upload_url,
                exc,
                exc_info=True,
            )
            return None

        return {"id": asset_id, "hostedUrl": hosted_url}

    async def add_draft(self, item: dict, is_draft: bool = True) -> str:
        """Create a CMS item (draft or live) and return the Webflow-assigned item ID."""
        title = item.get("title", "")
        slug = _make_slug(title)
        seo_description = _truncate_title(item.get("seo_description", ""), 160)
        field_data: Dict[str, Any] = {
            "name": title,
            "slug": slug,
            "random": _truncate_title(item.get("seo_title", title), 60),
            "short-description": seo_description,
            "news-description": _style_lists(_reformat_sources(item.get("html", ""))),
            "date": item.get("published_at", ""),
            "min-read": item.get("reading_time", "1 min read"),
            "featured-on-top": False,
            "latest-news": True,
            "main-hero-news": False,
            "highlighted-news": False,
            "premium-content": False,
        }
        image_asset = item.get("image_asset")
        if image_asset and self._image_field:
            field_data[self._image_field] = {
                "fileId": image_asset.get("id", ""),
                "url": image_asset.get("hostedUrl", ""),
                "alt": f"Featured image for: {title}",
            }
        author_id = item.get("author_id")
        if author_id:
            field_data[self._author_field] = author_id
        category_id = item.get("category_id")
        if category_id:
            field_data[self._category_field] = category_id
        payload = {
            "fieldData": field_data,
            "isArchived": False,
            "isDraft": is_draft,
        }
        resp = await self._client.post(
            f"/collections/{self._collection_id}/items",
            json=payload,
        )
        for _ in range(5):
            if resp.is_success:
                break
            if resp.status_code == 400 and "slug" in resp.text.lower():
                payload["fieldData"]["slug"] = f"{slug}-{uuid.uuid4().hex[:8]}"
                resp = await self._client.post(
                    f"/collections/{self._collection_id}/items",
                    json=payload,
                )
            else:
                break
        if not resp.is_success:
            raise RuntimeError(
                f"Webflow add_draft failed: HTTP {resp.status_code} — {resp.text}"
            )
        return str(resp.json().get("id", ""))

    async def list_authors(self, authors_collection_id: str) -> List[Dict[str, Any]]:
        """Fetch all items from the Authors collection. Returns empty list on error."""
        all_authors: List[Dict[str, Any]] = []
        offset = 0
        try:
            while True:
                resp = await self._client.get(
                    f"/collections/{authors_collection_id}/items",
                    params={"limit": _PAGE_LIMIT, "offset": offset},
                )
                if not resp.is_success:
                    logger.warning(
                        "Failed to fetch authors (HTTP %s) — publishing without author assignment",
                        resp.status_code,
                    )
                    return []
                data = resp.json()
                items = data.get("items", [])
                all_authors.extend(items)
                offset += len(items)
                if len(items) < _PAGE_LIMIT:
                    break
        except Exception as exc:
            logger.warning("Error fetching authors: %s — publishing without author assignment", exc)
            return []
        return all_authors

    async def list_categories(self, categories_collection_id: str) -> List[Dict[str, Any]]:
        """Fetch all items from the Categories collection. Returns empty list on error."""
        all_categories: List[Dict[str, Any]] = []
        offset = 0
        try:
            while True:
                resp = await self._client.get(
                    f"/collections/{categories_collection_id}/items",
                    params={"limit": _PAGE_LIMIT, "offset": offset},
                )
                if not resp.is_success:
                    logger.warning(
                        "Failed to fetch categories (HTTP %s) — publishing without category assignment",
                        resp.status_code,
                    )
                    return []
                data = resp.json()
                items = data.get("items", [])
                all_categories.extend(items)
                offset += len(items)
                if len(items) < _PAGE_LIMIT:
                    break
        except Exception as exc:
            logger.warning("Error fetching categories: %s — publishing without category assignment", exc)
            return []
        return all_categories

    async def _fetch_page(self, offset: int) -> Dict[str, Any]:
        """Fetch one page of collection items. Raises on rate-limit or HTTP error."""
        # Webflow v2 does not support cursor pagination; offset-based pagination can skip/repeat
        # items if drafts are added between pages. Acceptable here since dedup is best-effort.
        resp = await self._client.get(
            f"/collections/{self._collection_id}/items",
            params={"limit": _PAGE_LIMIT, "offset": offset},
        )
        if resp.status_code == 429:
            raise RuntimeError("Webflow API rate limit exceeded (HTTP 429). Wait before retrying.")
        resp.raise_for_status()
        return resp.json()

    async def list_items(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Fetch all collection items, optionally filtered to those on or after `since`."""
        all_items: List[Dict[str, Any]] = []
        offset = 0

        while True:
            data = await self._fetch_page(offset)
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
