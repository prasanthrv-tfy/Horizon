## ADDED Requirements

### Requirement: Publisher config accepts authors collection settings
`PublisherConfig` SHALL accept two new optional fields: `authors_collection_id` (str, default `""`) identifying the Webflow Authors collection, and `author_field` (str, default `"author"`) naming the reference field slug in the blog CMS collection.

#### Scenario: Config with authors_collection_id set
- **WHEN** `data/config.json` contains `"authors_collection_id": "<id>"` under `publisher`
- **THEN** `PublisherConfig` parses it without error and exposes it as `publisher_config.authors_collection_id`

#### Scenario: Config without authors_collection_id
- **WHEN** `data/config.json` has no `authors_collection_id` key under `publisher`
- **THEN** `PublisherConfig.authors_collection_id` defaults to `""` and the publish run proceeds without author assignment

---

### Requirement: Publisher fetches all authors from Webflow at run start
When `authors_collection_id` is configured, the publisher SHALL fetch all items from that Webflow collection before the per-post loop begins. Pagination SHALL be used to retrieve all authors regardless of collection size.

#### Scenario: Authors collection has items
- **WHEN** `authors_collection_id` is set and the Webflow Authors collection contains one or more items
- **THEN** all author item dicts are returned, each containing at least an `"id"` field

#### Scenario: Authors collection is empty
- **WHEN** `authors_collection_id` is set but the Authors collection has no items
- **THEN** a warning is logged and the run continues; no author is assigned to any post

#### Scenario: Fetch fails (API error)
- **WHEN** `authors_collection_id` is set but the Webflow API returns an error
- **THEN** a warning is logged and the run continues without author assignment (fail open)

#### Scenario: authors_collection_id is not configured
- **WHEN** `authors_collection_id` is empty string
- **THEN** no fetch is attempted and author assignment is skipped silently

---

### Requirement: Each post is assigned a randomly selected author
For each post being published, the system SHALL select one author uniformly at random from the fetched author list and set the author reference on the post before pushing to Webflow.

#### Scenario: Author assigned per post
- **WHEN** authors were successfully fetched and a post is being published
- **THEN** `field_data[author_field]` is set to the `"id"` of a randomly chosen author item

#### Scenario: Different posts may receive different authors
- **WHEN** multiple posts are published in the same run and multiple authors exist
- **THEN** each post independently samples from the full author list (uniform random, per post)

#### Scenario: No authors available
- **WHEN** the author list is empty (fetch failed or returned no items)
- **THEN** `field_data` is pushed to Webflow without an author field; the post is still published
