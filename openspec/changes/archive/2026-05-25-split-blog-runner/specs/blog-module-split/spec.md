## ADDED Requirements

### Requirement: loader module provides data-loading utilities
The system SHALL provide a `src/blog/loader.py` module containing `_clean_title`, `load_important_items`, and `resolve_profiles` extracted from `runner.py` with identical signatures and behaviour.

#### Scenario: load_important_items reads pipeline output
- **WHEN** `load_important_items(path)` is called with a valid JSON path
- **THEN** it returns the same `List[ContentItem]` that the original function in runner.py returned

#### Scenario: load_important_items exits on missing file
- **WHEN** `load_important_items(path)` is called with a path that does not exist
- **THEN** it prints an error and calls `sys.exit(1)`, same as the original

#### Scenario: resolve_profiles resolves "all"
- **WHEN** `resolve_profiles("all")` is called
- **THEN** it returns all registered profiles from `PROFILES`

### Requirement: enricher module provides thin-item enrichment
The system SHALL provide a `src/blog/enricher.py` module containing `_enrich_one` and `enrich_thin_items` extracted from `runner.py` with identical async behaviour and concurrency controls.

#### Scenario: enrich_thin_items skips items with sufficient content
- **WHEN** `enrich_thin_items` is called and an item already has a long description
- **THEN** that item is returned unchanged

#### Scenario: enrich_thin_items enriches items concurrently
- **WHEN** multiple thin items are present
- **THEN** they are enriched concurrently using the same semaphore limit as the original implementation

### Requirement: scorer module provides scoring and ranking logic
The system SHALL provide a `src/blog/scorer.py` module containing `rank_by_relevance`, `_score_single_item`, `score_items_for_profile`, and `_compute_weighted_sum` extracted from `runner.py` with identical scoring behaviour.

#### Scenario: score_items_for_profile applies gate-based filtering
- **WHEN** `score_items_for_profile` is called with a profile that has `scoring_dimensions`
- **THEN** it returns the same `List[ScoredItem]` with inclusion decisions as the original

#### Scenario: rank_by_relevance is used when no scoring_dimensions defined
- **WHEN** `rank_by_relevance` is called for a profile without `scoring_dimensions`
- **THEN** it returns items ranked by the LLM relevance score, same as the original

### Requirement: reporter module provides reporting and persistence
The system SHALL provide a `src/blog/reporter.py` module containing `_write_ranking_results` and `_write_run_log` extracted from `runner.py` with identical file output.

#### Scenario: _write_ranking_results generates the same markdown file
- **WHEN** `_write_ranking_results` is called with scored items and profiles
- **THEN** it writes `artifacts/ranking_results.md` with content identical to the original implementation

#### Scenario: _write_run_log generates the same JSON log
- **WHEN** `_write_run_log` is called after a blog run
- **THEN** it writes a JSON log to `artifacts/blog-runs/` with the same schema as the original

### Requirement: runner.py remains the CLI entry point
The system SHALL keep `src/blog/runner.py` as the CLI entry point, containing only `generate_and_save_posts`, `_run`, and `main`, delegating all other work to the new modules.

#### Scenario: horizon-blog CLI behaves identically after refactor
- **WHEN** `uv run horizon-blog --rank-only --profile news` is executed
- **THEN** it produces the same output and artifacts as before the refactor

#### Scenario: runner imports from new modules
- **WHEN** `runner.py` is imported
- **THEN** it successfully imports `loader`, `enricher`, `scorer`, and `reporter` from the `src/blog` package with no circular import errors
