## MODIFIED Requirements

### Requirement: Two-pass deduplication before publishing
The publisher SHALL apply two deduplication passes before publishing any post:
1. **Pass 1 (title match)**: Normalised exact-title match against all fetched Webflow items. Posts matched here are immediately skipped.
2. **Pass 2 (semantic match)**: For each post that survives Pass 1, an LLM call checks whether the post title covers the same news event as any existing Webflow item title. This check is performed lazily inside the publish loop — only for posts that would otherwise be published — and stops once the publish limit is reached.

#### Scenario: Exact duplicate caught by title match
- **WHEN** a new post title normalises to the same string as an existing Webflow item
- **THEN** the post is skipped before any LLM call is made and counted in the title-match skip total

#### Scenario: Semantic duplicate caught by LLM
- **WHEN** a new post title survives title normalisation but the LLM determines it covers the same story as an existing Webflow item
- **THEN** the post is skipped without calling `add_draft` and is counted in the semantic-match skip total

#### Scenario: LLM dedup is skipped after publish limit reached
- **WHEN** the publish limit (`max_drafts`) has been reached during the loop
- **THEN** remaining candidate posts are not sent to the LLM and are not published

#### Scenario: LLM semantic check fails
- **WHEN** the LLM call for semantic dedup raises an exception or returns unparseable output
- **THEN** the post is treated as NOT a duplicate and proceeds to publication (fail open)

#### Scenario: Distinct posts are not suppressed
- **WHEN** a new post title is semantically different from all existing Webflow item titles
- **THEN** the post is published normally

## ADDED Requirements

### Requirement: Skipped-post summary distinguishes skip reason
The end-of-run summary SHALL report title-match skips and semantic-match skips separately so the operator can understand how many posts were caught by each pass.

#### Scenario: Summary shows both skip types
- **WHEN** at least one post is skipped by title match and at least one by semantic match
- **THEN** the console output labels them distinctly (e.g., `[title]` vs `[semantic]`)
