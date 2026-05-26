## Context

`WebflowPublisher` in `src/blog/publisher/webflow.py` already implements `list_items`, `get_item`, and `add_draft` against the Webflow Staged Items API v2. Two methods remain as `NotImplementedError` stubs: `publish_draft` and `delete_item`. The Webflow API exposes both as collection-level endpoints that accept arrays, even though our interface wraps them as single-item calls.

## Goals / Non-Goals

**Goals:**
- Implement `publish_draft(item_id)` using `POST /collections/{collection_id}/items/publish`
- Implement `delete_item(item_id)` using `DELETE /collections/{collection_id}/items`
- Raise clearly on partial failures (publish) and HTTP errors (delete)

**Non-Goals:**
- Batch publish/delete APIs (single-item wrapping is sufficient for current runner usage)
- Locale-aware publish or delete (no multi-locale support needed)
- Changes to `runner.py` or any caller — this is purely filling in the stubs

## Decisions

### publish_draft: check publishedItemIds, not just status code

The Webflow publish endpoint returns HTTP 202 even on partial failure, with separate `publishedItemIds` and `errors` arrays. Checking only the status code would silently swallow failures. The implementation will raise `RuntimeError` if `item_id` is absent from `publishedItemIds` or present in `errors`.

*Alternative considered*: return a bool instead of raising — rejected because the abstract contract is `-> None` and callers (the runner) already wrap in try/except expecting exceptions for failures.

### delete_item: raise_for_status is sufficient

The delete endpoint returns 204 No Content on success and a structured error body on failure. Unlike publish, there's no partial-success ambiguity — `raise_for_status()` is the right check.

### Single-item wrapping over batch

Both Webflow endpoints accept arrays. We wrap each as a single-item call to match the `Publisher` abstract interface. A future `publish_drafts(ids)` batch method can be added to `WebflowPublisher` directly without touching the abstract base.

## Risks / Trade-offs

- **publish_draft partial-failure format** — If Webflow changes the `errors` field structure between API versions, our check could miss failures. Mitigation: also assert `item_id in publishedItemIds` as the positive check, making it robust regardless of error format.
- **delete is permanent** — No soft-delete or undo. Mitigation: callers are responsible for intent; nothing in the runner calls `delete_item` today.
