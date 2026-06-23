## ADDED Requirements

### Requirement: Publisher config accepts categories collection settings
`PublisherConfig` SHALL accept two new optional fields: `categories_collection_id` (str, default `""`) identifying the Webflow Categories collection, and `category_field` (str, default `"category-2"`) naming the reference field slug in the blog CMS collection.

#### Scenario: Config with categories_collection_id set
- **WHEN** `data/config.json` contains `"categories_collection_id": "<id>"` under `publisher`
- **THEN** `PublisherConfig` parses it without error and exposes it as `publisher_config.categories_collection_id`

#### Scenario: Config without categories_collection_id
- **WHEN** `data/config.json` has no `categories_collection_id` key under `publisher`
- **THEN** `PublisherConfig.categories_collection_id` defaults to `""` and the publish run proceeds without category assignment

---

### Requirement: Publisher fetches all categories from Webflow at run start
When `categories_collection_id` is configured, the publisher SHALL fetch all items from that Webflow collection before the per-post loop begins. Pagination SHALL be used to retrieve all categories regardless of collection size.

#### Scenario: Categories collection has items
- **WHEN** `categories_collection_id` is set and the Webflow Categories collection contains one or more items
- **THEN** all category item dicts are returned, each containing at least `"id"` and `fieldData.name`

#### Scenario: Categories collection is empty
- **WHEN** `categories_collection_id` is set but the Categories collection has no items
- **THEN** a warning is logged and the run continues; no category is assigned to any post

#### Scenario: Fetch fails (API error)
- **WHEN** `categories_collection_id` is set but the Webflow API returns an error
- **THEN** a warning is logged and the run continues without category assignment (fail open)

#### Scenario: categories_collection_id is not configured
- **WHEN** `categories_collection_id` is empty string
- **THEN** no fetch is attempted and category assignment is skipped silently

---

### Requirement: LLM selects the most relevant category per post
For each post being published, the system SHALL call an LLM with the post title, tags, and available category names to determine the best-matching category.

#### Scenario: LLM returns a matching category name
- **WHEN** categories were successfully fetched and the LLM returns a name that exists in the fetched list
- **THEN** `field_data[category_field]` is set to the Webflow item ID corresponding to that name

#### Scenario: LLM returns an unrecognised name
- **WHEN** the LLM returns a name that does not match any fetched category
- **THEN** no category is assigned and the post publishes without a category field

#### Scenario: LLM call fails
- **WHEN** the AI call throws an exception or returns unparseable output
- **THEN** a warning is logged, no category is assigned, and the post still publishes (fail open)

#### Scenario: No categories available
- **WHEN** the categories list is empty (fetch failed or returned no items)
- **THEN** the LLM is not called; the post publishes without a category field

---

### Requirement: Category assignment uses title and tags as input signals
The LLM prompt SHALL include the article title and its tags as the primary signals for category selection, alongside the list of available category names.

#### Scenario: Post has tags
- **WHEN** a post has non-empty tags
- **THEN** both title and tags are included in the prompt sent to the LLM

#### Scenario: Post has no tags
- **WHEN** a post has an empty tags list
- **THEN** the title alone is used as the signal; the LLM call still proceeds