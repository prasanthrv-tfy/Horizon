#!/usr/bin/env python3
"""Export a Webflow collection to a local JSON file.

Usage:
    uv run python scripts/webflow/export_collection.py --collection [news|authors|categories]
    uv run python scripts/webflow/export_collection.py --collection news --since-days 30
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

WEBFLOW_API = "https://api.webflow.com/v2"
PAGE_LIMIT = 100

ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "data" / "config.json"
OUTPUT_DIR = ROOT / "artifacts" / "webflow"

COLLECTION_CONFIG_KEYS = {
    "news": ["blog", "publisher", "collection_id"],
    "authors": ["blog", "publisher", "authors_collection_id"],
    "categories": ["blog", "publisher", "categories_collection_id"],
}


def _resolve_collection_id(cfg: dict, collection: str) -> str:
    keys = COLLECTION_CONFIG_KEYS[collection]
    node = cfg
    for key in keys:
        node = node.get(key, {})
    if not isinstance(node, str) or not node:
        print(f"✗ Could not resolve collection ID for '{collection}' from data/config.json", file=sys.stderr)
        sys.exit(1)
    return node


async def fetch_all(token: str, collection_id: str, since: datetime | None = None) -> list:
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
    }
    items = []
    offset = 0
    async with httpx.AsyncClient(base_url=WEBFLOW_API, headers=headers) as client:
        while True:
            resp = await client.get(
                f"/collections/{collection_id}/items",
                params={"limit": PAGE_LIMIT, "offset": offset},
            )
            if not resp.is_success:
                print(f"✗ Webflow API error: HTTP {resp.status_code} — {resp.text}", file=sys.stderr)
                sys.exit(1)
            data = resp.json()
            page = data.get("items", [])
            if since is not None:
                page = [item for item in page if _published_after(item, since)]
            items.extend(page)
            offset += len(data.get("items", []))
            if len(data.get("items", [])) < PAGE_LIMIT:
                break
    return items


def _published_after(item: dict, since: datetime) -> bool:
    since_utc = since.replace(tzinfo=timezone.utc) if since.tzinfo is None else since
    for key in ("lastPublished", "createdOn"):
        raw = item.get(key)
        if raw and isinstance(raw, str):
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                dt_utc = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
                return dt_utc >= since_utc
            except ValueError:
                pass
    return True


def main() -> None:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="Export a Webflow collection to JSON.")
    parser.add_argument(
        "--collection",
        choices=["news", "authors", "categories"],
        required=True,
        help="Which collection to export.",
    )
    parser.add_argument(
        "--since-days",
        metavar="N",
        type=int,
        default=None,
        help="Only include items published/created in the last N days (news only).",
    )
    args = parser.parse_args()

    token = os.environ.get("WEBFLOW_TOKEN")
    if not token:
        print("✗ WEBFLOW_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    if not CONFIG_PATH.exists():
        print(f"✗ Config not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    collection_id = _resolve_collection_id(cfg, args.collection)

    since = None
    if args.since_days is not None:
        since = datetime.now(tz=timezone.utc) - timedelta(days=args.since_days)

    print(f"Fetching '{args.collection}' collection ({collection_id})...")
    items = asyncio.run(fetch_all(token, collection_id, since=since))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{args.collection}.json"
    output_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Saved {len(items)} items to {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
