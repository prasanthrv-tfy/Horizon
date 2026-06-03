## Why

When the blog pipeline runs daily, the top-scored items are often about ongoing stories already published to Webflow. Deduplication currently happens at publish time — after per-item scoring LLM calls and full post generation — so the pipeline wastes work and can silently produce zero new posts.

## What Changes

- Add a `create_publisher(config, token) -> Publisher` factory to `publisher/__init__.py` so any code that needs a publisher gets one through the abstract interface, never by importing `WebflowPublisher` directly.
- Refactor `publisher/runner.py` to use the factory instead of instantiating `WebflowPublisher` directly.
- Add `batch_semantic_dedup(source_items, webflow_items, ai_client)` to `publisher/deduplicator.py` — one LLM call that checks all source candidates against all recently published Webflow posts at once.
- Add a pre-filter step in `generator/runner.py` that runs **before** scoring: queries Webflow via the factory, calls `batch_semantic_dedup`, and removes already-covered items from the candidate pool. If the pool becomes empty, generation is skipped cleanly. If Webflow is not configured, pre-filtering is silently skipped and the publisher's existing dedup remains the safety net.

## Capabilities

### New Capabilities
- `publisher-factory`: `create_publisher(config, token) -> Publisher` factory exposed from `publisher/__init__.py`; both the generator pre-filter and the publisher runner use it — no code outside the publisher module imports `WebflowPublisher` directly.
- `pre-generation-dedup`: pre-filter step in the generator that queries recently published Webflow items and removes semantic duplicate candidates before scoring runs.

### Modified Capabilities
- `publish-deduplication`: adds `batch_semantic_dedup` to `deduplicator.py` — a many-to-many LLM check (N source items vs M Webflow items, one call) complementing the existing one-to-many `semantic_is_duplicate`.

## Impact

- `src/blog/publisher/__init__.py` — new factory function
- `src/blog/publisher/deduplicator.py` — new `batch_semantic_dedup` function
- `src/blog/publisher/runner.py` — replace direct `WebflowPublisher` instantiation with factory
- `src/blog/generator/runner.py` — new pre-filter step before `score_items_for_profile`
- Requires `WEBFLOW_TOKEN` env var and `blog.publisher.collection_id` in config to activate pre-filtering; both are already used by the publisher, no new config fields needed
