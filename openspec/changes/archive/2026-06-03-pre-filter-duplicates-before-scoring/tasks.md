## 1. Publisher Factory

- [x] 1.1 Add `create_publisher(config: PublisherConfig, token: str) -> Publisher` to `src/blog/publisher/__init__.py`; it returns `WebflowPublisher(token=token, collection_id=config.collection_id)` with no validation
- [x] 1.2 Refactor `src/blog/publisher/runner.py` to import `create_publisher` from `. ` and replace the direct `WebflowPublisher(token=token, collection_id=collection_id)` instantiation; keep the `collection_id` empty-check and `sys.exit` in the runner, before the factory call

## 2. Batch Semantic Dedup

- [x] 2.1 Add `batch_semantic_dedup(source_items: list[dict], webflow_items: list[dict], ai_client) -> set[str]` to `src/blog/publisher/deduplicator.py`; return empty set immediately if `webflow_items` is empty
- [x] 2.2 Write the batch prompt: system prompt reuses "exact same news event or announcement" guidelines from `_SEMANTIC_DEDUP_SYSTEM`; user prompt lists source items (index, title, summary) and existing posts (index, title, description); expected JSON response is `{"duplicates": [<source_indices>]}`
- [x] 2.3 Parse the LLM response, map returned indices back to source item IDs, return as a set; on any exception log a warning and return an empty set (fail open)

## 3. Generator Pre-Filter

- [x] 3.1 In `src/blog/generator/runner.py`, after `load_important_items` and before the profile loop, add `async def _prefilter_duplicates(items, config, console) -> list[ContentItem]` that: checks for `WEBFLOW_TOKEN` and non-empty `collection_id`, skips silently if either is absent, queries Webflow via `create_publisher`, calls `batch_semantic_dedup`, and returns the filtered item list
- [x] 3.2 Wire `_prefilter_duplicates` into `_run`: call it on `items` after enrichment, reassign result to `items`; if `items` becomes empty after pre-filter, print a notice and return early before the profile loop
- [x] 3.3 Apply `deduplication_time_window` from `PublisherConfig` when calling `list_items(since=...)` in the pre-filter (same window as the publisher runner uses)
