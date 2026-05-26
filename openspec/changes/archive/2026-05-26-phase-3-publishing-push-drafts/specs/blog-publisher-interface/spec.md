## MODIFIED Requirements

### Requirement: WebflowPublisher implementation
The system SHALL provide a `WebflowPublisher` class in `src/blog/publisher/webflow.py` that extends `Publisher` and targets the Webflow Staged Items API. In Phase 3, `list_items`, `get_item`, and `add_draft` SHALL all be fully implemented; `publish_draft` and `delete_item` remain as `NotImplementedError` stubs.

#### Scenario: Construction with token and collection_id
- **WHEN** `WebflowPublisher` is instantiated with a `token` and `collection_id`
- **THEN** it SHALL initialise an `httpx.AsyncClient` with the Bearer auth header set

#### Scenario: list_items returns real data
- **WHEN** `list_items()` is called on a `WebflowPublisher` with a valid token and collection_id
- **THEN** it SHALL return a list of item dicts fetched from the Webflow API

#### Scenario: get_item returns real data
- **WHEN** `get_item(item_id)` is called on a `WebflowPublisher` with a valid token and collection_id
- **THEN** it SHALL return the item dict fetched from the Webflow API

#### Scenario: add_draft creates a draft and returns item ID
- **WHEN** `add_draft` is called with a valid post dict
- **THEN** it SHALL POST to the Webflow API and return the new item's string ID

#### Scenario: publish_draft raises NotImplementedError
- **WHEN** `publish_draft` is called
- **THEN** it SHALL raise `NotImplementedError`
