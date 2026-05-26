## Context

Phase 1 scaffolded `WebflowPublisher` with stub methods and a dry-run CLI. The `list_items` and `get_item` methods raise `NotImplementedError`. The `horizon-publish` CLI discovers local posts but has no way to know which ones already exist in Webflow.

Phase 2 makes `list_items` real and adds a deduplication pass so the CLI can show (and later act on) a filtered candidate list.

Webflow Staged Items API reference:
- List: `GET /v2/collections/{collection_id}/items` — returns paginated items with `fieldData.name` (title) and date fields
- Get: `GET /v2/collections/{collection_id}/items/{item_id}`

## Goals / Non-Goals

**Goals:**
- Implement `WebflowPublisher.list_items(since)` with full pagination support
- Implement `WebflowPublisher.get_item(item_id)`
- Add `deduplicate_posts()` — title-normalised matching between local posts and Webflow items
- Wire dedup into `horizon-publish` CLI output (kept vs. skipped summary)

**Non-Goals:**
- Semantic or embedding-based deduplication (deferred)
- Actually creating drafts (Phase 3)
- Matching on URL or slug (title match only in this phase)

## Decisions

### 1. Title normalisation for matching

Raw title comparison is fragile — Webflow may add/remove punctuation, and local post filenames encode titles differently. Normalise both sides before comparison:

```
normalise(t) = t.lower().strip(), collapsed whitespace, remove punctuation
```

A local post is considered a duplicate if its normalised title matches any Webflow item's normalised `fieldData.name`.

*Alternative*: slug matching — rejected because slugs are not always stored in Webflow items from previous manual uploads.

### 2. Deduplication in a separate module

`deduplicator.py` owns title normalisation and the filter function. This keeps `webflow.py` focused on API I/O and makes the dedup logic independently testable without mocking HTTP.

### 3. Pagination via `offset` parameter

Webflow's collection items API supports `limit` + `offset` query params. `list_items` will loop until the returned page is smaller than the limit (standard offset pagination), fetching up to a configurable max (default 100 per page).

*Alternative*: cursor-based pagination — Webflow doesn't use cursors for this endpoint, offset is the correct approach.

### 4. `since` filter applied client-side

The Webflow API does not support server-side date filtering on collection items. `list_items(since)` fetches all pages and filters by `lastPublished` or `createdOn` date client-side. For a `deduplication_time_window` of 14 days this means fetching at most a few hundred items — acceptable.

### 5. `collection_id` required at runtime

If `blog.publisher.collection_id` is empty, `horizon-publish` exits with a clear error before making any API calls. This prevents silent failures where all posts appear to be "new" because no collection was checked.

## Risks / Trade-offs

- **Webflow field name changes** — `fieldData.name` is assumed to be the title field. If the collection uses a different field name, dedup silently passes everything through.  
  → Mitigation: log a warning if `fieldData.name` is absent on fetched items.

- **Large collections** — For collections with thousands of items, the client-side date filter still fetches all pages before filtering.  
  → Accepted for now; the time window bounds the relevant set. Can add a server-side `sort` + early exit in a future phase.

- **Rate limiting** — Webflow free tier has low rate limits. Paginated fetching of many pages could hit limits.  
  → Mitigation: `httpx` responses include `Retry-After` headers; raise a clear error if a 429 is received.

## Open Questions

- None for Phase 2. Draft creation details are handled in Phase 3.
