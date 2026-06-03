## ADDED Requirements

### Requirement: batch_semantic_dedup function in deduplicator.py
The system SHALL provide a `batch_semantic_dedup(source_items, webflow_items, ai_client)` async function in `src/blog/publisher/deduplicator.py`. It SHALL issue a single LLM call that checks all source items against all existing Webflow posts and returns a set of source item IDs that are semantic duplicates of any existing post.

`source_items` is a list of dicts with `id`, `title`, and `summary` keys. `webflow_items` is a list of dicts with `title` and `description` keys (matching the shape already built in `publisher/runner.py`).

#### Scenario: All candidates are novel
- **WHEN** none of the source items cover the same story as any Webflow post
- **THEN** `batch_semantic_dedup` SHALL return an empty set

#### Scenario: Some candidates are duplicates
- **WHEN** a subset of source items cover the same stories as existing Webflow posts
- **THEN** `batch_semantic_dedup` SHALL return a set containing the `id` values of only those matching source items

#### Scenario: All candidates are duplicates
- **WHEN** every source item covers a story already in Webflow
- **THEN** `batch_semantic_dedup` SHALL return a set containing all source item IDs

#### Scenario: No existing Webflow items
- **WHEN** `webflow_items` is an empty list
- **THEN** `batch_semantic_dedup` SHALL return an empty set without making an LLM call

#### Scenario: LLM call fails
- **WHEN** the LLM call raises an exception or returns unparseable output
- **THEN** `batch_semantic_dedup` SHALL log a warning and return an empty set (fail open)

### Requirement: batch_semantic_dedup uses a single LLM call
The function SHALL issue exactly one LLM call regardless of how many source items or Webflow items are provided.

#### Scenario: Single LLM call for N source items
- **WHEN** `batch_semantic_dedup` is called with 30 source items and 20 Webflow items
- **THEN** it SHALL make exactly one call to `ai_client.complete`

### Requirement: batch_semantic_dedup applies the same duplicate criteria as semantic_is_duplicate
The batch check SHALL use the same "exact same news event or announcement" guideline as the existing `semantic_is_duplicate` function. Different coverage angles of the same product are not duplicates.

#### Scenario: Same event is a duplicate
- **WHEN** a source item and a Webflow post describe the same product release or announcement
- **THEN** the source item SHALL be included in the returned duplicate set

#### Scenario: Different angle of same product is not a duplicate
- **WHEN** a source item covers a different update to the same product as an existing Webflow post
- **THEN** the source item SHALL NOT be included in the returned duplicate set
