## Why

`src/blog/runner.py` has grown to ~711 lines containing five distinct logical concerns in one file — data loading, content enrichment, AI scoring/ranking, reporting/persistence, and CLI orchestration — making it hard to navigate, test, or modify individual subsystems without touching everything.

## What Changes

- Extract data-loading helpers into `src/blog/loader.py` (`load_important_items`, `resolve_profiles`, `_clean_title`)
- Extract content-enrichment logic into `src/blog/enricher.py` (`enrich_thin_items`, `_enrich_one`)
- Extract all scoring and ranking logic into `src/blog/scorer.py` (`score_items_for_profile`, `_score_single_item`, `_compute_weighted_sum`, `rank_by_relevance`)
- Extract reporting and persistence logic into `src/blog/reporter.py` (`_write_ranking_results`, `_write_run_log`)
- Slim `src/blog/runner.py` down to ~70 lines — only `generate_and_save_posts`, `_run`, and `main`
- No behavior changes; the `horizon-blog` CLI entry point and all public interfaces remain identical

## Capabilities

### New Capabilities

- `blog-module-split`: Decompose `src/blog/runner.py` into focused single-responsibility modules (`loader`, `enricher`, `scorer`, `reporter`) while keeping `runner.py` as a thin orchestrator

### Modified Capabilities

<!-- No requirement-level changes; this is a pure structural refactor -->

## Impact

- **Files created**: `src/blog/loader.py`, `src/blog/enricher.py`, `src/blog/scorer.py`, `src/blog/reporter.py`
- **Files modified**: `src/blog/runner.py` (shrunk, imports from new modules)
- **Entry point unchanged**: `pyproject.toml` `horizon-blog = "src.blog.runner:main"` stays as-is
- **No API changes**: All public function signatures remain identical; internal helpers move but are not part of any public API
- **No new dependencies**: Uses only imports already present in `runner.py`
