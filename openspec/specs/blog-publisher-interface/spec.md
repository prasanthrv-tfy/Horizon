## ADDED Requirements

### Requirement: Abstract Publisher base class
The system SHALL provide an abstract `Publisher` base class in `src/blog/publisher/publisher.py` that defines the CMS contract all publisher implementations must satisfy.

#### Scenario: Instantiating an incomplete implementation
- **WHEN** a class subclasses `Publisher` without implementing all abstract methods
- **THEN** instantiation SHALL raise `TypeError`

#### Scenario: Correct implementation passes instantiation
- **WHEN** a class subclasses `Publisher` and implements all abstract methods
- **THEN** it SHALL instantiate without error

### Requirement: Publisher add_draft method
The `Publisher` base class SHALL declare an abstract `add_draft(item: BlogPost) -> str` method that creates a draft CMS item and returns its provider-assigned ID.

#### Scenario: Draft creation contract
- **WHEN** `add_draft` is called with a `BlogPost` item
- **THEN** the implementation SHALL create a draft in the CMS and return the item's string ID

### Requirement: Publisher list_items method
The `Publisher` base class SHALL declare an abstract `list_items(since: datetime | None = None) -> list` method that returns CMS collection items, optionally filtered to those created/published on or after `since`.

#### Scenario: List all items
- **WHEN** `list_items()` is called with no arguments
- **THEN** the implementation SHALL return all items in the collection

#### Scenario: List items since a date
- **WHEN** `list_items(since=<datetime>)` is called
- **THEN** the implementation SHALL return only items on or after that datetime

### Requirement: Publisher get_item method
The `Publisher` base class SHALL declare an abstract `get_item(item_id: str) -> dict` method that retrieves a single CMS item by its ID.

#### Scenario: Get existing item
- **WHEN** `get_item` is called with a valid item ID
- **THEN** the implementation SHALL return the item's data as a dict

### Requirement: Publisher publish_draft method
The `Publisher` base class SHALL declare an abstract `publish_draft(item_id: str) -> None` method that promotes a draft item to live.

#### Scenario: Publish draft
- **WHEN** `publish_draft` is called with a valid draft item ID
- **THEN** the implementation SHALL make the item live in the CMS

### Requirement: Publisher delete_item method
The `Publisher` base class SHALL declare an abstract `delete_item(item_id: str) -> None` method that removes an item from the collection.

#### Scenario: Delete item
- **WHEN** `delete_item` is called with a valid item ID
- **THEN** the implementation SHALL remove that item from the CMS collection

### Requirement: WebflowPublisher implementation
The system SHALL provide a `WebflowPublisher` class in `src/blog/publisher/webflow.py` that extends `Publisher` and targets the Webflow Staged Items API. All five methods — `list_items`, `get_item`, `add_draft`, `publish_draft`, and `delete_item` — SHALL be fully implemented.

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

#### Scenario: publish_draft promotes a draft to live
- **WHEN** `publish_draft` is called with a valid draft item ID
- **THEN** it SHALL POST to `/collections/{collection_id}/items/publish` and raise `RuntimeError` if the item is absent from `publishedItemIds` or present in `errors`

#### Scenario: delete_item removes the item
- **WHEN** `delete_item` is called with a valid item ID
- **THEN** it SHALL send `DELETE /collections/{collection_id}/items` with the item ID and raise on non-2xx

### Requirement: Deduplication module
The system SHALL provide a `deduplicate_posts()` function in `src/blog/publisher/deduplicator.py` that accepts a list of local post paths and a list of Webflow item dicts, and returns `(kept, skipped)` — posts whose normalised title does not match any Webflow item's normalised `fieldData.name` are kept.

#### Scenario: No duplicates
- **WHEN** none of the local post titles match any Webflow item title
- **THEN** `deduplicate_posts()` SHALL return all local posts in `kept` and an empty `skipped`

#### Scenario: All duplicates
- **WHEN** every local post title matches a Webflow item title
- **THEN** `deduplicate_posts()` SHALL return an empty `kept` list

#### Scenario: Partial duplicates
- **WHEN** some local post titles match Webflow items and some do not
- **THEN** `deduplicate_posts()` SHALL return only the non-matching posts in `kept`

### Requirement: Title normalisation
Title normalisation SHALL lowercase the string, strip leading/trailing whitespace, collapse internal whitespace to single spaces, and remove all punctuation before comparison.

#### Scenario: Case-insensitive match
- **WHEN** a local post title is "GPT-5 Arrives" and a Webflow item has `fieldData.name` "gpt-5 arrives"
- **THEN** they SHALL be considered duplicates

#### Scenario: Punctuation-insensitive match
- **WHEN** a local post title is "AI: The Future!" and a Webflow item has `fieldData.name` "AI The Future"
- **THEN** they SHALL be considered duplicates

### Requirement: PublisherConfig model
The system SHALL provide a `PublisherConfig` Pydantic model nested under `BlogConfig` with `collection_id: str` (default `""`) and `deduplication_time_window: int` (default `14`, in days).

#### Scenario: Config with no publisher key
- **WHEN** `data/config.json` has a `blog` section with no `publisher` key
- **THEN** `BlogConfig` SHALL validate successfully with default `PublisherConfig` values

#### Scenario: Config with publisher overrides
- **WHEN** `data/config.json` specifies `blog.publisher.collection_id` and `blog.publisher.deduplication_time_window`
- **THEN** those values SHALL be reflected in the loaded `PublisherConfig`
