# Blog Content Prefetch Spec

## Requirements

### Requirement: Thin items are enriched before scoring

Before multi-dimensional scoring runs, the blog runner SHALL attempt to enrich any item whose `content` field is shorter than 500 characters by fetching the item's URL or falling back to a web search. Enrichment updates `item.content` in-memory only — the source file `data/pipeline-output/important_items.json` is never modified.

#### Scenario: Item content is short — fetch succeeds
- **GIVEN** an item with `len(content) < 500`
- **WHEN** an HTTP GET of `item.url` returns a 200 response
- **THEN** `item.content` is replaced with the first 2000 chars of stripped plain text from the response
- **AND** the console logs a success line for that item

#### Scenario: Item content is short — fetch fails, search succeeds
- **GIVEN** an item with `len(content) < 500`
- **WHEN** the HTTP GET of `item.url` fails (non-200, timeout, network error, or returned text < 200 chars)
- **THEN** a DuckDuckGo search is performed using the item title and top two tags
- **AND** `item.content` is replaced with the concatenated top-3 search result snippets
- **AND** the console logs a warning that fetch failed and search was used

#### Scenario: Item content is short — both fetch and search fail
- **GIVEN** an item with `len(content) < 500`
- **WHEN** both the URL fetch and the search fallback fail or return empty results
- **THEN** `item.content` is left unchanged (original thin content)
- **AND** the console logs that enrichment failed for that item
- **AND** scoring proceeds with the original content (no crash, no skip)

#### Scenario: Item content is already sufficient
- **GIVEN** an item with `len(content) >= 500`
- **WHEN** `enrich_thin_items` runs
- **THEN** the item is skipped entirely — no fetch, no search, no modification to `item.content`

---

### Requirement: Enrichment is in-memory only

The enrichment step SHALL NOT write any changes back to `data/pipeline-output/important_items.json` or any other file on disk.

#### Scenario: Source file unchanged after run
- **WHEN** `uv run horizon-blog` completes
- **THEN** `data/pipeline-output/important_items.json` has the same content as before the run

---

### Requirement: Enrichment runs once, shared across all profiles

When multiple profiles are run (e.g., `prompt_profile: "all"`), enrichment SHALL run once before the profile loop, not once per profile.

#### Scenario: Two profiles, enrichment runs once
- **GIVEN** `prompt_profile` is `"all"` with two registered profiles
- **WHEN** `horizon-blog` runs
- **THEN** enrichment log lines appear once per item, not twice

---

### Requirement: Scorer sees more content after enrichment

The content preview passed to `_score_single_item` SHALL use the first 1500 characters of `item.content` (up from 400).

#### Scenario: Enriched content reaches scorer
- **GIVEN** an item whose content was enriched from 160 chars to 1800 chars
- **WHEN** `_score_single_item` builds the item text
- **THEN** the content preview contains up to 1500 chars of the enriched content