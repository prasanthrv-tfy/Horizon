## Why

The blog module currently generates markdown posts but has no way to publish them anywhere. Phase 1 lays the structural foundation for a publishing pipeline by reorganising the blog module and scaffolding the publisher abstraction — so that Phases 2 and 3 can build on a clean, stable base.

## What Changes

- Move all generation files (`runner.py`, `writer.py`, `scorer.py`, `enricher.py`, `fetcher.py`, `loader.py`, `reporter.py`, `prompts.py`) from `src/blog/` into `src/blog/generator/`
- Keep shared files (`models.py`, `profiles/`) at the `src/blog/` level
- Create `src/blog/publisher/` with an abstract `Publisher` base class and a `WebflowPublisher` implementation (Webflow API wired up, dedup and push logic stubbed)
- Add `horizon-publish` CLI entry point in `pyproject.toml` that reads `artifacts/blog-posts/` and logs what it would publish (no actual API calls yet)
- Extend `BlogConfig` with `publisher.collection_id` and `publisher.deduplication_time_window` (default 14 days)

## Capabilities

### New Capabilities

- `blog-publisher-interface`: Abstract `Publisher` base class defining the CMS contract (`add_draft`, `list_items`, `get_item`, `publish_draft`, `delete_item`) and the `WebflowPublisher` implementation backed by the Webflow Staged Items API
- `horizon-publish-cli`: The `horizon-publish` CLI entry point — reads generated blog post files, instantiates the publisher, and runs the publish pipeline (stubbed in Phase 1)

### Modified Capabilities

- `blog-generator-module`: Current `src/blog/` generation files relocated to `src/blog/generator/` subpackage; all internal imports updated accordingly

## Impact

- **`src/blog/`**: Restructured — generator files move to `src/blog/generator/`, shared files stay
- **`src/blog/publisher/`**: New subpackage added
- **`src/models.py` / `src/blog/models.py`**: `BlogConfig` gains `publisher` nested config (`collection_id`, `deduplication_time_window`)
- **`pyproject.toml`**: New `horizon-publish` script entry point added
- **`CLAUDE.md`**: Updated with new CLI command and module layout
- **All import sites** of `src/blog.*` (orchestrator, tests) updated to new paths
- **Dependencies**: No new runtime deps in Phase 1 (`httpx` already present for Webflow HTTP calls)
