#!/usr/bin/env python3
"""Delete every item in a Webflow collection.

Usage:
    uv run python scripts/webflow/clear_collection.py --collection news                  # dry-run
    uv run python scripts/webflow/clear_collection.py --collection news --execute         # confirm + delete
    uv run python scripts/webflow/clear_collection.py --collection news --execute --yes   # skip confirmation
    uv run python scripts/webflow/clear_collection.py --collection-id 6a3224... --execute --yes
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

WEBFLOW_API = "https://api.webflow.com/v2"
PAGE_LIMIT = 100

ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "data" / "config.json"

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


async def fetch_all(client: httpx.AsyncClient, collection_id: str) -> list:
    items = []
    offset = 0
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
        items.extend(page)
        offset += len(page)
        if len(page) < PAGE_LIMIT:
            break
    return items


def _describe_conflict(resp: httpx.Response) -> str:
    try:
        body = resp.json()
    except ValueError:
        return resp.text
    refs = []
    for detail in body.get("details", []):
        for conflict in detail.get("conflicts", []):
            ref = conflict.get("ref", {})
            refs.append(f"{ref.get('name', ref.get('id'))} (in {ref.get('collectionName', ref.get('collectionId'))})")
    if refs:
        return f"still referenced by: {', '.join(refs)}"
    return body.get("message", resp.text)


async def delete_item(client: httpx.AsyncClient, collection_id: str, item_id: str, name: str) -> str:
    """Delete one item. Returns 'deleted', 'conflict', or 'failed'."""
    resp = await client.request(
        "DELETE",
        f"/collections/{collection_id}/items",
        json={"items": [{"id": item_id}]},
    )
    if resp.is_success:
        print(f"  ✓ deleted {name} ({item_id})")
        return "deleted"
    if resp.status_code == 409:
        print(f"  ✗ conflict deleting {name} ({item_id}): {_describe_conflict(resp)}", file=sys.stderr)
        return "conflict"
    print(f"  ✗ failed to delete {name} ({item_id}): HTTP {resp.status_code} — {resp.text}", file=sys.stderr)
    return "failed"


async def run(token: str, collection_id: str, execute: bool, skip_confirm: bool) -> None:
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(base_url=WEBFLOW_API, headers=headers, timeout=httpx.Timeout(30.0)) as client:
        items = await fetch_all(client, collection_id)
        names = [item.get("fieldData", {}).get("name", "<unnamed>") for item in items]

        print(f"Would delete {len(items)} items from collection {collection_id}:")
        for name in names:
            print(f"  - {name}")

        if not execute:
            print("\nDry-run complete. Re-run with --execute to apply this change.")
            return

        if not skip_confirm:
            answer = input(f"\nType 'yes' to confirm deleting {len(items)} items: ")
            if answer.strip().lower() != "yes":
                print("Aborted.")
                return

        print(f"\nDeleting {len(items)} items...")
        deleted = conflicts = failed = 0
        for item in items:
            item_id = str(item.get("id", ""))
            name = item.get("fieldData", {}).get("name", "<unnamed>")
            outcome = await delete_item(client, collection_id, item_id, name)
            if outcome == "deleted":
                deleted += 1
            elif outcome == "conflict":
                conflicts += 1
            else:
                failed += 1

        print(f"\n✓ Done. Deleted {deleted}/{len(items)} ({conflicts} conflicts, {failed} other failures).")


def main() -> None:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="Delete every item in a Webflow collection.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--collection",
        choices=sorted(COLLECTION_CONFIG_KEYS),
        help="Named collection to clear, resolved from data/config.json.",
    )
    group.add_argument(
        "--collection-id",
        help="Raw Webflow collection ID to clear (bypasses data/config.json).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete items. Without this flag, only a dry-run preview is printed.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt when used with --execute.",
    )
    args = parser.parse_args()

    token = os.environ.get("WEBFLOW_TOKEN")
    if not token:
        print("✗ WEBFLOW_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    if args.collection_id:
        collection_id = args.collection_id
    else:
        if not CONFIG_PATH.exists():
            print(f"✗ Config not found at {CONFIG_PATH}", file=sys.stderr)
            sys.exit(1)
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        collection_id = _resolve_collection_id(cfg, args.collection)

    asyncio.run(run(token, collection_id, execute=args.execute, skip_confirm=args.yes))


if __name__ == "__main__":
    main()
