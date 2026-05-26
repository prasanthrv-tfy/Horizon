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
The system SHALL provide a `WebflowPublisher` class in `src/blog/publisher/webflow.py` that extends `Publisher` and targets the Webflow Staged Items API.

#### Scenario: Construction with token and collection_id
- **WHEN** `WebflowPublisher` is instantiated with a `token` and `collection_id`
- **THEN** it SHALL initialise an `httpx.AsyncClient` with the Bearer auth header set

#### Scenario: Phase 1 stub methods raise NotImplementedError
- **WHEN** any of the publisher methods (`add_draft`, `list_items`, `get_item`, `publish_draft`, `delete_item`) are called in Phase 1
- **THEN** they SHALL raise `NotImplementedError`

### Requirement: PublisherConfig model
The system SHALL provide a `PublisherConfig` Pydantic model nested under `BlogConfig` with `collection_id: str` (default `""`) and `deduplication_time_window: int` (default `14`, in days).

#### Scenario: Config with no publisher key
- **WHEN** `data/config.json` has a `blog` section with no `publisher` key
- **THEN** `BlogConfig` SHALL validate successfully with default `PublisherConfig` values

#### Scenario: Config with publisher overrides
- **WHEN** `data/config.json` specifies `blog.publisher.collection_id` and `blog.publisher.deduplication_time_window`
- **THEN** those values SHALL be reflected in the loaded `PublisherConfig`
