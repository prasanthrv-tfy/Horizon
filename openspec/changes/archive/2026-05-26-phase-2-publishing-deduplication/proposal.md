## Why

Without deduplication, running `horizon-publish` multiple times (or after re-running `horizon-blog`) would create duplicate drafts in Webflow for articles already in the collection. Phase 2 adds the deduplication gate that filters out posts already present in the collection before any drafts are created.

## What Changes

- Implement `WebflowPublisher.list_items(since)` — fetches staged/published items from the Webflow collection via the API, optionally filtered by date
- Add `deduplicate_posts()` function in the publisher module that normalises titles and filters out posts whose titles already appear in the Webflow collection
- Wire deduplication into the `horizon-publish` CLI: fetch existing items within the `deduplication_time_window`, filter the discovered local posts, log which were kept and which were dropped

## Capabilities

### New Capabilities

- `webflow-list-items`: The `WebflowPublisher.list_items(since)` method — real Webflow API call with pagination support, returns normalised item dicts

### Modified Capabilities

- `blog-publisher-interface`: `WebflowPublisher` methods `list_items` and `get_item` are no longer stubs — they are now implemented against the Webflow API
- `horizon-publish-cli`: The CLI now deduplicates posts against the Webflow collection before printing the candidate list; the "dry-run" notice is replaced by a filtered summary showing kept vs. skipped items

## Impact

- **`src/blog/publisher/webflow.py`**: `list_items` and `get_item` fully implemented
- **`src/blog/publisher/deduplicator.py`**: New module with title normalisation and dedup logic
- **`src/blog/publisher/runner.py`**: Updated to call dedup before listing candidates
- **`data/config.json`**: `blog.publisher.collection_id` must now be set for the CLI to proceed
- **Dependencies**: No new runtime deps (`httpx` already present)
