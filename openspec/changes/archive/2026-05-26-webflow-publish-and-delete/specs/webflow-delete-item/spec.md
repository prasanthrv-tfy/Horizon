## ADDED Requirements

### Requirement: WebflowPublisher delete_item implementation
`WebflowPublisher.delete_item(item_id: str) -> None` SHALL remove a CMS item by sending `DELETE /collections/{collection_id}/items` with `{"items": [{"id": item_id}]}`.

#### Scenario: Successful delete
- **WHEN** `delete_item` is called with a valid item ID
- **THEN** it SHALL send the DELETE request and return without error on HTTP 204

#### Scenario: Non-2xx response
- **WHEN** the Webflow API returns a non-2xx status code
- **THEN** `delete_item` SHALL raise `RuntimeError` with the status code and response body
