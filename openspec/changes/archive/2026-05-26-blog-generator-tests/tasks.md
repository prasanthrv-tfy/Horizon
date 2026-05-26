## 1. Shared test fixtures

- [x] 1.1 Define `make_content_item` helper that builds a minimal `ContentItem` with controllable `id`, `title`, `content`, `ai_tags`, and `ai_score`
- [x] 1.2 Define `MockAIClient` with an async `complete()` coroutine that returns a configurable JSON string

## 2. Pure function tests (`tests/test_blog_generator_utils.py`)

- [x] 2.1 Test `_clean_title`: emoji prefix stripped, clean ASCII unchanged, empty string, mixed emoji+text
- [x] 2.2 Test `BlogWriter._make_slug`: special chars removed, spaces → hyphens, truncated at 80 chars, lowercase
- [x] 2.3 Test `_strip_html`: script/style blocks removed, visible paragraph text extracted, plain text passthrough
- [x] 2.4 Test `_compute_weighted_sum`: correct total for known weights+scores, zero-weight dimension contributes nothing

## 3. File I/O tests (`tests/test_blog_generator_utils.py`, continued)

- [x] 3.1 Test `load_important_items`: valid JSON returns `ContentItem` list; missing file raises `SystemExit`; empty array raises `SystemExit`
- [x] 3.2 Test `resolve_profiles`: known name returns single profile; `"all"` returns all profiles; unknown name raises `SystemExit`
- [x] 3.3 Test `_write_run_log`: file created at `artifacts/blog-runs/YYYY-MM-DD-{profile}.json`; JSON contains `profile`, `items_evaluated`, `items_included`, `items_excluded`, `results` keys (use `monkeypatch.chdir(tmp_path)`)
- [x] 3.4 Test `_write_ranking_results`: `artifacts/ranking_results.md` created; profile name present in file content (use `monkeypatch.chdir(tmp_path)`)

## 4. Async gate-path scoring tests (`tests/test_blog_generator_scorer.py`)

- [x] 4.1 Test `score_items_for_profile` — item passes all gates: `included=True`, `inclusion_path` matches path name
- [x] 4.2 Test `score_items_for_profile` — item fails one dimension: `included=False`, failing dimension in `failed_gates`
- [x] 4.3 Test `score_items_for_profile` — two paths, fails A passes B: `included=True`, `inclusion_path` is path B name
- [x] 4.4 Test `score_items_for_profile` — AI returns empty/malformed: all scores 0, item excluded, no exception raised
- [x] 4.5 Test `score_items_for_profile` — `weighted_sum` uses winning path's weights (not another path's)
- [x] 4.6 Test `rank_by_relevance` — valid `ranked_ids` response: items returned in specified order
- [x] 4.7 Test `rank_by_relevance` — AI raises exception: original order returned, no exception propagated
- [x] 4.8 Test `rank_by_relevance` — single item input: returned immediately without calling AI client

## 5. Async enrichment chain tests (`tests/test_blog_generator_enricher.py`)

- [x] 5.1 Test `enrich_thin_items` — rich item (content ≥ 500 chars) not passed to `fetch_url` or `search_fallback`
- [x] 5.2 Test `enrich_thin_items` — thin item: `fetch_url` succeeds → item content updated to fetched text
- [x] 5.3 Test `enrich_thin_items` — thin item: `fetch_url` raises → `search_fallback` called → item content updated
- [x] 5.4 Test `enrich_thin_items` — thin item: both `fetch_url` raises and `search_fallback` returns `""` → item content unchanged
- [x] 5.5 Test `enrich_thin_items` — empty item list: returns without error and without instantiating `ContentFetcher`

## 6. Verify

- [x] 6.1 Run `uv run pytest tests/test_blog_generator_utils.py tests/test_blog_generator_scorer.py tests/test_blog_generator_enricher.py -v` and confirm all tests pass
