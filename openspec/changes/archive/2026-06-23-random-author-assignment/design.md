## Context

The Webflow publisher (`src/blog/publisher/`) pushes blog posts to Webflow CMS via the Staged Items API. Posts are built as dicts and handed to `WebflowPublisher.add_draft()`, which constructs `fieldData` for the CMS item. Webflow supports reference fields that point to items in other collections — the blog collection has an `"author"` reference field that accepts an Author item ID from a separate Authors collection. Currently no author is set, so all posts appear authorless.

## Goals / Non-Goals

**Goals:**
- Fetch all available authors from the Webflow Authors collection at the start of each publish run
- Assign one randomly selected author to each post before pushing to Webflow
- Fail open: if authors cannot be fetched or the list is empty, posts publish without an author (no run failure)
- Keep author config alongside existing publisher config in `data/config.json`

**Non-Goals:**
- Weighted author distribution (pure uniform random only)
- Caching authors across runs
- Allowing per-post author override from the blog generator

## Decisions

### 1. Authors fetched once per run, not per post

Fetching authors once before the post loop and sampling from the in-memory list avoids N redundant API calls. The Authors collection changes rarely; staleness within a single run is not a concern.

**Alternative considered**: fetch a random author inline in `add_draft` — rejected because it couples the publisher to knowledge of the authors collection and multiplies API calls.

### 2. `list_authors` is a method on `WebflowPublisher`, not a separate client

The publisher already holds an authenticated `httpx.AsyncClient` pointed at the Webflow API base URL. Reusing it avoids threading credentials into a second object. `list_authors` accepts `authors_collection_id` as a parameter (not stored on `self`) since the publisher's primary identity is the blog collection.

**Alternative considered**: a second `WebflowPublisher` instantiated with the authors collection ID — rejected as unnecessarily heavy; no pagination or dedup behavior is needed for authors.

### 3. Author ID passed through the post dict, not as a parameter to `add_draft`

`image_asset` is already injected into the post dict before `add_draft` is called. Extending the same pattern (`post["author_id"] = ...`) keeps `add_draft`'s signature stable and makes all field overrides visible at the call site in `runner.py`.

### 4. `author_field` configurable, defaulting to `"author"`

The Webflow field slug is `"author"` in the known deployment, but making it configurable costs nothing and avoids a code change if the field is renamed.

## Risks / Trade-offs

- **Authors collection returns no items** → logged as a warning; run continues without authors. Acceptable since posts are still published.
- **Authors collection ID misconfigured** → fetch will return an HTTP error. Treated the same as empty: warn and continue.
- **Non-uniform distribution over time** → pure `random.choice` is uniform per post but not guaranteed to distribute evenly across a small number of posts in a single run. Acceptable for the stated requirement.

## Migration Plan

1. Add `authors_collection_id` and `author_field` to `PublisherConfig` with empty/default values — fully backward compatible; existing runs without these fields set behave identically to today.
2. Deploy code changes.
3. Update `data/config.json` with the actual Webflow Authors collection ID to activate the feature.

No rollback concern — if the fields are left empty, the feature is a no-op.
