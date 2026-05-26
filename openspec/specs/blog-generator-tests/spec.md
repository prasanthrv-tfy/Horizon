### Requirement: Pure function tests
The test suite SHALL verify the deterministic utility functions in the blog generator with no external dependencies.

#### Scenario: _clean_title strips leading emoji
- **WHEN** a title begins with one or more emoji or non-ASCII characters
- **THEN** `_clean_title` returns the title with those leading characters removed

#### Scenario: _clean_title passes through clean ASCII title
- **WHEN** a title contains only printable ASCII characters
- **THEN** `_clean_title` returns the title unchanged

#### Scenario: _make_slug produces URL-safe slug
- **WHEN** a title contains special characters, spaces, and mixed case
- **THEN** `BlogWriter._make_slug` returns a lowercase hyphen-separated string with no special characters

#### Scenario: _make_slug truncates at 80 characters
- **WHEN** a title is longer than 80 characters
- **THEN** the resulting slug is at most 80 characters long

#### Scenario: _strip_html removes script and style tags with their content
- **WHEN** HTML input contains `<script>` or `<style>` blocks
- **THEN** `_strip_html` returns plain text with those blocks removed entirely

#### Scenario: _strip_html extracts visible text
- **WHEN** HTML input contains paragraphs and headings
- **THEN** `_strip_html` returns the visible text content

#### Scenario: _compute_weighted_sum sums correctly
- **WHEN** a gate path has dimensions with known weights and scores
- **THEN** `_compute_weighted_sum` returns the correct weighted total rounded to 3 decimal places

#### Scenario: _compute_weighted_sum with zero-weight dimension
- **WHEN** a dimension has weight 0
- **THEN** that dimension contributes nothing to the weighted sum

### Requirement: File I/O tests
The test suite SHALL verify functions that read from and write to the filesystem.

#### Scenario: load_important_items loads valid JSON
- **WHEN** a valid JSON file containing content item dicts exists at the given path
- **THEN** `load_important_items` returns a list of `ContentItem` objects

#### Scenario: load_important_items exits on missing file
- **WHEN** the given path does not exist
- **THEN** `load_important_items` calls `sys.exit(1)`

#### Scenario: load_important_items exits on empty array
- **WHEN** the JSON file contains an empty array
- **THEN** `load_important_items` calls `sys.exit(0)`

#### Scenario: resolve_profiles returns single profile by name
- **WHEN** a valid profile name is given
- **THEN** `resolve_profiles` returns a list containing exactly that profile

#### Scenario: resolve_profiles returns all profiles for "all"
- **WHEN** the name is `"all"`
- **THEN** `resolve_profiles` returns all registered profiles

#### Scenario: resolve_profiles exits on unknown profile
- **WHEN** an unknown profile name is given
- **THEN** `resolve_profiles` calls `sys.exit(1)`

#### Scenario: _write_run_log creates JSON at expected path
- **WHEN** called with a list of scored items and a profile name
- **THEN** a JSON file is created at `artifacts/blog-runs/YYYY-MM-DD-{profile}.json` with keys `profile`, `items_evaluated`, `items_included`, `items_excluded`, and `results`

#### Scenario: _write_ranking_results creates markdown file
- **WHEN** called with profiles_scored data
- **THEN** `artifacts/ranking_results.md` is created and contains the profile name

### Requirement: Async gate-path scoring tests
The test suite SHALL verify the gate-path evaluation logic in `score_items_for_profile` and the fallback ranking in `rank_by_relevance` using a mocked AI client.

#### Scenario: item passes all gates
- **WHEN** the AI returns scores above all thresholds for all dimensions in a gate path
- **THEN** the resulting `ScoredItem` has `included=True` and `inclusion_path` set to that path's name

#### Scenario: item fails one dimension threshold
- **WHEN** the AI returns a score below the threshold for one dimension
- **THEN** the resulting `ScoredItem` has `included=False` and `failed_gates` lists that dimension

#### Scenario: item passes second gate path when first fails
- **WHEN** an item fails path A but all dimensions in path B are above threshold
- **THEN** the resulting `ScoredItem` has `included=True` and `inclusion_path` set to path B

#### Scenario: AI returns empty response
- **WHEN** the AI client returns an empty or malformed response
- **THEN** all dimension scores default to 0, the item is excluded, and no exception is raised

#### Scenario: weighted_sum uses winning path weights
- **WHEN** an item is included via a specific gate path
- **THEN** `weighted_sum` reflects that path's dimension weights, not another path's

#### Scenario: rank_by_relevance reorders items
- **WHEN** the AI returns a `ranked_ids` list in a different order than the input
- **THEN** `rank_by_relevance` returns items in the order specified by `ranked_ids`

#### Scenario: rank_by_relevance returns original order on AI failure
- **WHEN** the AI client raises an exception
- **THEN** `rank_by_relevance` returns items in their original order without raising

#### Scenario: rank_by_relevance skips single-item list
- **WHEN** the input list has exactly one item
- **THEN** `rank_by_relevance` returns it immediately without calling the AI client

### Requirement: Async enrichment chain tests
The test suite SHALL verify the `enrich_thin_items` fetch-then-search fallback logic.

#### Scenario: rich items are not enriched
- **WHEN** an item's content is at or above `THIN_CONTENT_THRESHOLD` (500 chars)
- **THEN** `enrich_thin_items` does not call `fetch_url` or `search_fallback` for that item

#### Scenario: thin item is enriched via URL fetch
- **WHEN** an item's content is below the threshold and `fetch_url` succeeds
- **THEN** the item's content is replaced with the fetched text

#### Scenario: thin item falls back to search when fetch fails
- **WHEN** `fetch_url` raises an exception but `search_fallback` returns text
- **THEN** the item's content is replaced with the search result text

#### Scenario: thin item content unchanged when both fetch and search fail
- **WHEN** both `fetch_url` raises and `search_fallback` returns empty string
- **THEN** the item's content is not changed

#### Scenario: empty item list completes without error
- **WHEN** `enrich_thin_items` is called with an empty list
- **THEN** it returns immediately without creating a `ContentFetcher` or making network calls
