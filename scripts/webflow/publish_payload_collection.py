#!/usr/bin/env python3
"""Create Webflow collection items from a JSON payload file.

Usage:
    uv run python scripts/webflow/publish_payload_collection.py --collection authors --payload data/authors_payload.json
    uv run python scripts/webflow/publish_payload_collection.py --collection authors --payload data/authors_payload.json --execute
    uv run python scripts/webflow/publish_payload_collection.py --collection authors --payload data/authors_payload.json --execute --yes
    uv run python scripts/webflow/publish_payload_collection.py --collection-id 6a3224... --payload path/to/other.json --execute --yes
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


async def create_item(client: httpx.AsyncClient, collection_id: str, field_data: dict) -> str | None:
    name = field_data.get("name", "<unnamed>")
    resp = await client.post(
        f"/collections/{collection_id}/items",
        json={"fieldData": field_data, "isArchived": False, "isDraft": False},
    )
    if resp.is_success:
        item_id = str(resp.json().get("id", ""))
        print(f"  ✓ created {name} ({item_id})")
        return item_id
    print(f"  ✗ failed to create {name}: HTTP {resp.status_code} — {resp.text}", file=sys.stderr)
    return None


async def publish_items(client: httpx.AsyncClient, collection_id: str, item_ids: list) -> int:
    """Promote staged items to live. Webflow items stay 'Queued for publish' until this is called."""
    if not item_ids:
        return 0
    resp = await client.post(
        f"/collections/{collection_id}/items/publish",
        json={"itemIds": item_ids},
    )
    if not resp.is_success:
        print(f"  ✗ failed to publish items: HTTP {resp.status_code} — {resp.text}", file=sys.stderr)
        return 0
    data = resp.json()
    published = set(data.get("publishedItemIds", []))
    errors = set(data.get("errors", []))
    for item_id in item_ids:
        if item_id in published and item_id not in errors:
            print(f"  ✓ published {item_id}")
        else:
            print(f"  ✗ not published: {item_id}", file=sys.stderr)
    return len(published - errors)


async def run(token: str, collection_id: str, payload: list, execute: bool, skip_confirm: bool) -> None:
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(base_url=WEBFLOW_API, headers=headers, timeout=httpx.Timeout(30.0)) as client:
        names = [entry.get("name", "<unnamed>") for entry in payload]

        print(f"Would create {len(payload)} items in collection {collection_id}:")
        for name in names:
            print(f"  - {name}")

        if not execute:
            print("\nDry-run complete. Re-run with --execute to apply this change.")
            return

        if not skip_confirm:
            answer = input(f"\nType 'yes' to confirm creating {len(payload)} items: ")
            if answer.strip().lower() != "yes":
                print("Aborted.")
                return

        print(f"\nCreating {len(payload)} items...")
        created_ids = []
        for entry in payload:
            item_id = await create_item(client, collection_id, entry)
            if item_id:
                created_ids.append(item_id)

        print(f"\nPublishing {len(created_ids)} items...")
        published = await publish_items(client, collection_id, created_ids)

        print(f"\n✓ Done. Created {len(created_ids)}/{len(payload)}, published {published}/{len(created_ids)}.")


def main() -> None:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="Create Webflow collection items from a JSON payload file.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--collection",
        choices=sorted(COLLECTION_CONFIG_KEYS),
        help="Named collection to publish into, resolved from data/config.json.",
    )
    group.add_argument(
        "--collection-id",
        help="Raw Webflow collection ID to publish into (bypasses data/config.json).",
    )
    parser.add_argument(
        "--payload",
        type=Path,
        required=True,
        help="Path to a JSON array of fieldData objects to create as items.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually create items. Without this flag, only a dry-run preview is printed.",
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

    if not args.payload.exists():
        print(f"✗ Payload file not found at {args.payload}", file=sys.stderr)
        sys.exit(1)
    payload = json.loads(args.payload.read_text(encoding="utf-8"))

    asyncio.run(run(token, collection_id, payload, execute=args.execute, skip_confirm=args.yes))


if __name__ == "__main__":
    main()
