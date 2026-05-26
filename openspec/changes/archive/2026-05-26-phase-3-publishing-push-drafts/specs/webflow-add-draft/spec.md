## ADDED Requirements

### Requirement: WebflowPublisher add_draft posts to Webflow API
`WebflowPublisher.add_draft(item)` SHALL POST to `POST /v2/collections/{collection_id}/items` with a fully-formed CMS payload and return the Webflow-assigned item ID string.

#### Scenario: Successful draft creation
- **WHEN** `add_draft` is called with a valid post dict and the Webflow API returns 2xx
- **THEN** it SHALL return the string ID of the newly created Webflow item

#### Scenario: API error on draft creation
- **WHEN** the Webflow API returns a non-2xx response
- **THEN** `add_draft` SHALL raise a `RuntimeError` with the HTTP status code and response body in the message

### Requirement: Webflow CMS payload structure
The payload posted by `add_draft` SHALL conform to the Webflow Staged Items schema:

```json
{
  "fieldData": {
    "name": "<title>",
    "slug": "<url-safe slug>",
    "meta-title": "<SEO title ≤60 chars>",
    "meta-description": "<SEO description ≤160 chars>",
    "content": "<rich HTML>",
    "published-date": "<ISO 8601 datetime>",
    "min-read": "<N min read>",
    "featured-on-top": "false"
  },
  "isArchived": false,
  "isDraft": true
}
```

#### Scenario: Payload fields populated
- **WHEN** `add_draft` is called with a post dict containing title, slug, html, seo_title, seo_description, published_at, reading_time
- **THEN** each corresponding `fieldData` key SHALL be set to the correct value

#### Scenario: isDraft is always true
- **WHEN** `add_draft` is called
- **THEN** the payload SHALL always set `"isDraft": true` and `"isArchived": false`
