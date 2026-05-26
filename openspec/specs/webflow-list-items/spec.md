## ADDED Requirements

### Requirement: WebflowPublisher list_items fetches from API
`WebflowPublisher.list_items(since)` SHALL call the Webflow Staged Items API (`GET /v2/collections/{collection_id}/items`) and return all collection items as a list of dicts, each containing at minimum `id` and `fieldData.name`.

#### Scenario: Successful fetch with no date filter
- **WHEN** `list_items()` is called with no arguments
- **THEN** it SHALL return all items in the collection across all pages

#### Scenario: Successful fetch with date filter
- **WHEN** `list_items(since=<datetime>)` is called
- **THEN** it SHALL return only items whose `lastPublished` or `createdOn` date is on or after `since`

#### Scenario: Empty collection
- **WHEN** the Webflow collection contains no items
- **THEN** `list_items()` SHALL return an empty list

### Requirement: WebflowPublisher list_items paginates
`list_items` SHALL paginate through all result pages using Webflow's `limit` and `offset` query parameters until no more items are returned.

#### Scenario: Multi-page collection
- **WHEN** the collection has more items than the page limit
- **THEN** `list_items` SHALL fetch subsequent pages and return all items combined

### Requirement: WebflowPublisher list_items handles rate limiting
`WebflowPublisher.list_items` SHALL raise a `RuntimeError` with a clear message if the Webflow API responds with HTTP 429.

#### Scenario: Rate limit hit during pagination
- **WHEN** the API returns a 429 response during list_items
- **THEN** a `RuntimeError` SHALL be raised indicating rate limit was exceeded

### Requirement: WebflowPublisher get_item fetches from API
`WebflowPublisher.get_item(item_id)` SHALL call `GET /v2/collections/{collection_id}/items/{item_id}` and return the item as a dict.

#### Scenario: Existing item
- **WHEN** `get_item` is called with a valid item ID
- **THEN** it SHALL return the item dict with `id` and `fieldData` present

#### Scenario: Non-existent item
- **WHEN** `get_item` is called with an item ID that does not exist
- **THEN** it SHALL raise a `RuntimeError` with the HTTP status code in the message

### Requirement: collection_id required before API calls
`horizon-publish` SHALL verify that `blog.publisher.collection_id` is non-empty and exit with a clear error before making any Webflow API calls.

#### Scenario: Missing collection_id
- **WHEN** `blog.publisher.collection_id` is empty or not set in config
- **THEN** `horizon-publish` SHALL print an error and exit with a non-zero exit code

#### Scenario: collection_id present
- **WHEN** `blog.publisher.collection_id` is set
- **THEN** `horizon-publish` SHALL proceed to fetch existing items
