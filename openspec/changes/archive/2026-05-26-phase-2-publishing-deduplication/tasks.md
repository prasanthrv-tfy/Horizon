## 1. WebflowPublisher: list_items and get_item

- [x] 1.1 Implement `WebflowPublisher.list_items(since)` — `GET /v2/collections/{collection_id}/items` with `limit=100&offset=N` pagination loop; stop when page is empty
- [x] 1.2 Apply client-side date filter in `list_items`: keep only items where `lastPublished` or `createdOn` is on or after `since` (when provided)
- [x] 1.3 Log a warning if any fetched item is missing `fieldData.name`
- [x] 1.4 Raise `RuntimeError` with a clear message if the API responds with HTTP 429
- [x] 1.5 Implement `WebflowPublisher.get_item(item_id)` — `GET /v2/collections/{collection_id}/items/{item_id}`; raise `RuntimeError` on non-2xx response

## 2. Deduplication module

- [x] 2.1 Create `src/blog/publisher/deduplicator.py` with a `normalise_title(title: str) -> str` helper (lowercase, strip, collapse whitespace, remove punctuation)
- [x] 2.2 Implement `deduplicate_posts(posts: list[Path], webflow_items: list[dict]) -> tuple[list[Path], list[Path]]` — returns `(kept, skipped)` based on normalised title match against `fieldData.name`
- [x] 2.3 Extract the post title from the Markdown file's front matter `title:` field (fall back to filename stem if absent)

## 3. CLI: wire deduplication into horizon-publish

- [x] 3.1 Add `collection_id` validation in `runner.py` — exit with error if `blog.publisher.collection_id` is empty before any API call
- [x] 3.2 Load `BlogConfig` from `StorageManager` in `runner.py` and construct `WebflowPublisher` with token and `collection_id`
- [x] 3.3 Call `list_items(since=now - deduplication_time_window)` and log the count of items fetched from Webflow
- [x] 3.4 Pass local posts and Webflow items to `deduplicate_posts()` and print kept vs. skipped summary
- [x] 3.5 Replace the Phase 1 "[DRY RUN]" notice with the dedup-filtered output (kept posts labelled "would publish", skipped labelled "already in Webflow")

## 4. Verification

- [x] 4.1 Write unit tests for `normalise_title` covering case, punctuation, and whitespace scenarios
- [x] 4.2 Write unit tests for `deduplicate_posts` covering no-duplicates, all-duplicates, and partial-duplicates scenarios
- [x] 4.3 Run `uv run pytest` — all tests must pass
