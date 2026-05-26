## Context

`src/blog/generator/` contains the core blog pipeline: scoring items against multi-dimensional gate paths, enriching thin content, and generating posts. The existing publisher tests (`tests/test_publisher_*.py`) establish the project's test style — plain pytest, `tmp_path` for file I/O, and inline `unittest.mock` for external dependencies. No async test infrastructure is currently used, but `pytest-asyncio` is already in the dev dependencies.

## Goals / Non-Goals

**Goals:**
- Cover pure/deterministic functions with parametrized cases
- Cover file I/O paths (load, write) with `tmp_path` and `monkeypatch`
- Cover async gate-path logic by mocking the AI client
- Cover the enrichment fallback chain (fetch → search → unchanged)

**Non-Goals:**
- Testing `runner.py` (CLI orchestration) — too many side effects, better covered end-to-end
- Testing `writer.py`'s `_generate_single_post` in full — requires mocking AI + DDGS together; covered by integration tests
- Achieving 100% line coverage — focus on behaviourally meaningful cases

## Decisions

**Three test files by concern**
Split into `test_blog_generator_utils.py` (pure + I/O), `test_blog_generator_scorer.py` (async gate logic), and `test_blog_generator_enricher.py` (async enrichment). Mirrors the publisher split and keeps files focused.
- Alternative: single file. Rejected — scorer tests require `@pytest.mark.asyncio` and fixture setup that would clutter a flat file.

**Mock AI client as a simple async callable**
Build a minimal `MockAIClient` with a `.complete()` coroutine that returns a pre-set JSON string. No external mock library needed — keeps tests readable.
- Alternative: `unittest.mock.AsyncMock`. Viable, but a named helper is more readable and reusable across the scorer and enricher tests.

**`monkeypatch` for `sys.exit` paths in loader**
`load_important_items` and `resolve_profiles` call `sys.exit` on bad input. Use `pytest.raises(SystemExit)` to assert the exit code without patching.

**Patch `ContentFetcher` methods directly for enricher tests**
`enrich_thin_items` constructs a `ContentFetcher` internally. Patch `fetch_url` and `search_fallback` on the class with `monkeypatch` to control outcomes without spinning up HTTP.

## Risks / Trade-offs

- `_write_ranking_results` writes to `artifacts/ranking_results.md` relative to CWD — tests must `monkeypatch` the output path or run from the repo root. → Use `tmp_path` with `monkeypatch.chdir` or pass a patched `Path`.
- `score_items_for_profile` uses `asyncio.Semaphore` and `asyncio.gather` internally — the mock client must be awaitable on each call. → Ensure `MockAIClient.complete` is a true coroutine.

## Open Questions

- None — scope is clear.
