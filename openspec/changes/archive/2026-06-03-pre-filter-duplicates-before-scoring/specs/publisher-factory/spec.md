## ADDED Requirements

### Requirement: create_publisher factory in publisher/__init__.py
The system SHALL expose a `create_publisher(config: PublisherConfig, token: str) -> Publisher` function from `src/blog/publisher/__init__.py`. The factory SHALL return a `WebflowPublisher` instance constructed from the given config and token without performing any validation.

#### Scenario: Factory returns a Publisher instance
- **WHEN** `create_publisher` is called with a valid `PublisherConfig` and a non-empty token
- **THEN** it SHALL return an object that is an instance of `Publisher`

#### Scenario: Factory does not validate collection_id
- **WHEN** `create_publisher` is called with a `PublisherConfig` whose `collection_id` is an empty string
- **THEN** it SHALL return a `Publisher` instance without raising an error

### Requirement: Publisher runner uses the factory
`src/blog/publisher/runner.py` SHALL obtain its `Publisher` instance by calling `create_publisher` and SHALL NOT import `WebflowPublisher` directly.

#### Scenario: Publisher runner collection_id validation stays in runner
- **WHEN** `collection_id` is empty in config
- **THEN** `publisher/runner.py` SHALL print an error and exit before calling `create_publisher`

#### Scenario: No direct WebflowPublisher import outside publisher/__init__.py
- **WHEN** any file outside `src/blog/publisher/__init__.py` needs a Publisher instance
- **THEN** it SHALL import and call `create_publisher`, not import `WebflowPublisher` directly
