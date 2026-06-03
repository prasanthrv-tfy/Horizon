## ADDED Requirements

### Requirement: Pre-filter step runs before scoring in generator
`generator/runner.py` SHALL execute a pre-filter step after loading `important_items` and before calling `score_items_for_profile`. The pre-filter SHALL remove items already covered by recently published Webflow posts from the candidate pool.

#### Scenario: Pre-filter removes duplicate candidates
- **WHEN** `WEBFLOW_TOKEN` is set and `blog.publisher.collection_id` is non-empty and Webflow returns published posts that semantically match some candidate items
- **THEN** those matching items SHALL be removed from the candidate pool before scoring begins

#### Scenario: Scoring receives only non-duplicate items
- **WHEN** the pre-filter completes successfully
- **THEN** `score_items_for_profile` SHALL be called only with items that survived the pre-filter

#### Scenario: Empty pool after pre-filter exits cleanly
- **WHEN** all candidate items are identified as duplicates and the pool becomes empty
- **THEN** the generator SHALL print a notice and exit without calling scoring or generation

### Requirement: Pre-filter is skipped when Webflow is not configured
The pre-filter SHALL be silently skipped if `WEBFLOW_TOKEN` is absent from the environment or `blog.publisher.collection_id` is empty. The pipeline SHALL continue to scoring as normal.

#### Scenario: Missing WEBFLOW_TOKEN
- **WHEN** the `WEBFLOW_TOKEN` environment variable is not set
- **THEN** the pre-filter step SHALL be skipped without error or warning

#### Scenario: Empty collection_id
- **WHEN** `blog.publisher.collection_id` is an empty string
- **THEN** the pre-filter step SHALL be skipped without error or warning

### Requirement: Pre-filter fails open on Webflow query error
If the Webflow `list_items` call raises an exception during pre-filtering, the generator SHALL log a warning and continue with the full unfiltered candidate pool.

#### Scenario: Webflow API error during pre-filter
- **WHEN** the Webflow API returns an error or the request times out during the pre-filter query
- **THEN** the generator SHALL log a warning, retain all candidate items, and proceed to scoring

### Requirement: Pre-filter uses the publisher factory
The generator pre-filter SHALL obtain its `Publisher` instance via `create_publisher` from `src.blog.publisher` and SHALL NOT import `WebflowPublisher` directly.

#### Scenario: Generator has no direct Webflow dependency
- **WHEN** `generator/runner.py` is inspected for imports
- **THEN** it SHALL import `create_publisher` from `src.blog.publisher`, not `WebflowPublisher` from `src.blog.publisher.webflow`

### Requirement: Pre-filter respects deduplication_time_window
The pre-filter SHALL query Webflow for items published within `blog.publisher.deduplication_time_window` days (default 14), matching the window used by the publisher runner.

#### Scenario: Time window applied to Webflow query
- **WHEN** `deduplication_time_window` is set to 7 in config
- **THEN** the pre-filter SHALL call `list_items(since=now - 7 days)`
