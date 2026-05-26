## MODIFIED Requirements

### Requirement: WebflowPublisher implementation
The system SHALL provide a `WebflowPublisher` class in `src/blog/publisher/webflow.py` that extends `Publisher` and targets the Webflow Staged Items API. In Phase 2, `list_items` and `get_item` SHALL be fully implemented; `add_draft`, `publish_draft`, and `delete_item` remain as `NotImplementedError` stubs.

#### Scenario: Construction with token and collection_id
- **WHEN** `WebflowPublisher` is instantiated with a `token` and `collection_id`
- **THEN** it SHALL initialise an `httpx.AsyncClient` with the Bearer auth header set

#### Scenario: list_items returns real data
- **WHEN** `list_items()` is called on a `WebflowPublisher` with a valid token and collection_id
- **THEN** it SHALL return a list of item dicts fetched from the Webflow API (not raise NotImplementedError)

#### Scenario: get_item returns real data
- **WHEN** `get_item(item_id)` is called on a `WebflowPublisher` with a valid token and collection_id
- **THEN** it SHALL return the item dict fetched from the Webflow API (not raise NotImplementedError)

#### Scenario: add_draft still raises NotImplementedError
- **WHEN** `add_draft` is called in Phase 2
- **THEN** it SHALL raise `NotImplementedError` (implemented in Phase 3)

## ADDED Requirements

### Requirement: Deduplication module
The system SHALL provide a `deduplicate_posts()` function in `src/blog/publisher/deduplicator.py` that accepts a list of local post paths and a list of Webflow item dicts, and returns only the posts whose normalised title does not match any Webflow item's normalised `fieldData.name`.

#### Scenario: No duplicates
- **WHEN** none of the local post titles match any Webflow item title
- **THEN** `deduplicate_posts()` SHALL return all local posts unchanged

#### Scenario: All duplicates
- **WHEN** every local post title matches a Webflow item title
- **THEN** `deduplicate_posts()` SHALL return an empty list

#### Scenario: Partial duplicates
- **WHEN** some local post titles match Webflow items and some do not
- **THEN** `deduplicate_posts()` SHALL return only the non-matching posts

### Requirement: Title normalisation
Title normalisation SHALL lowercase the string, strip leading/trailing whitespace, collapse internal whitespace to single spaces, and remove all punctuation before comparison.

#### Scenario: Case-insensitive match
- **WHEN** a local post title is "GPT-5 Arrives" and a Webflow item has `fieldData.name` "gpt-5 arrives"
- **THEN** they SHALL be considered duplicates

#### Scenario: Punctuation-insensitive match
- **WHEN** a local post title is "AI: The Future!" and a Webflow item has `fieldData.name` "AI The Future"
- **THEN** they SHALL be considered duplicates
