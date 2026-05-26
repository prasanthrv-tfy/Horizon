## Why

`WebflowPublisher.publish_draft` and `delete_item` are currently `NotImplementedError` stubs, making the publisher interface incomplete. Implementing them closes out the Webflow CMS integration so the runner can promote drafts to live and remove unwanted items.

## What Changes

- Implement `WebflowPublisher.publish_draft(item_id)` — POSTs to `POST /collections/{collection_id}/items/publish` with `{"itemIds": [item_id]}`, raises on partial failure
- Implement `WebflowPublisher.delete_item(item_id)` — sends `DELETE /collections/{collection_id}/items` with `{"items": [{"id": item_id}]}`, raises on non-2xx
- Update the `blog-publisher-interface` spec to reflect these are now fully implemented (not stubs)

## Capabilities

### New Capabilities
- `webflow-publish-draft`: Promote a staged draft item to live via the Webflow Staged Items API
- `webflow-delete-item`: Delete a CMS item from a Webflow collection

### Modified Capabilities
- `blog-publisher-interface`: `publish_draft` and `delete_item` on `WebflowPublisher` are no longer stubs — update the requirement to reflect full implementation

## Impact

- `src/blog/publisher/webflow.py` — two methods implemented
- No changes to `publisher.py`, `runner.py`, or any other module
- No new dependencies
