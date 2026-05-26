## MODIFIED Requirements

### Requirement: horizon-publish dry-run in Phase 1
**REMOVED** — The Phase 1 dry-run behaviour (no API calls, no dedup) is replaced by the Phase 2 dedup-filtered summary below.

**Reason**: Phase 2 implements real Webflow API fetching. The CLI now connects to Webflow to check for duplicates before listing candidates.
**Migration**: No user-facing migration needed; `uv run horizon-publish` continues to be the command.

## ADDED Requirements

### Requirement: horizon-publish fetches existing Webflow items
The `horizon-publish` CLI SHALL call `WebflowPublisher.list_items(since)` using the configured `deduplication_time_window` to retrieve existing collection items before processing local posts.

#### Scenario: Items fetched successfully
- **WHEN** `horizon-publish` runs with a valid `WEBFLOW_TOKEN` and `collection_id`
- **THEN** it SHALL fetch Webflow items from the past `deduplication_time_window` days and print the count of items found

### Requirement: horizon-publish deduplicates before listing candidates
The `horizon-publish` CLI SHALL pass discovered local posts and fetched Webflow items through `deduplicate_posts()`, then display a summary of kept and skipped posts.

#### Scenario: Some posts filtered
- **WHEN** deduplication finds matching titles between local posts and Webflow items
- **THEN** the CLI SHALL print a "skipped (already in Webflow)" line for each duplicate and a "would publish" line for each remaining post

#### Scenario: No duplicates found
- **WHEN** no local post titles match any Webflow item
- **THEN** the CLI SHALL print all discovered posts as candidates with no skipped items

#### Scenario: All posts are duplicates
- **WHEN** all local posts match Webflow items
- **THEN** the CLI SHALL print a message indicating no new posts to publish and exit cleanly

### Requirement: horizon-publish validates collection_id before API calls
The `horizon-publish` CLI SHALL verify `blog.publisher.collection_id` is non-empty and exit with a clear error if it is missing, before attempting any Webflow API call.

#### Scenario: Missing collection_id
- **WHEN** `blog.publisher.collection_id` is empty or absent from config
- **THEN** the CLI SHALL print an error message and exit with a non-zero exit code
