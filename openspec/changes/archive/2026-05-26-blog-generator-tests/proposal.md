## Why

The blog generation module (`src/blog/generator/`) has no test coverage. The gate-path scoring logic, content loading, HTML stripping, and enrichment chain are business-critical and change frequently — having tests will catch regressions when profiles or thresholds are adjusted.

## What Changes

- Add three new test files covering the blog generator module
- Tests cover pure functions, file I/O, async gate-path scoring, and the enrichment chain
- No production code changes

## Capabilities

### New Capabilities

- `blog-generator-tests`: Unit tests for `src/blog/generator/` — pure functions (`_clean_title`, `_make_slug`, `_strip_html`, `_compute_weighted_sum`), file I/O (`load_important_items`, `resolve_profiles`, `_write_run_log`, `_write_ranking_results`), async gate scoring (`score_items_for_profile`, `rank_by_relevance`), and the enrichment chain (`enrich_thin_items`)

### Modified Capabilities

## Impact

- New files: `tests/test_blog_generator_utils.py`, `tests/test_blog_generator_scorer.py`, `tests/test_blog_generator_enricher.py`
- No changes to `src/` — tests only
- Requires `pytest-asyncio` for async test cases (already available via `uv sync --extra dev`)
