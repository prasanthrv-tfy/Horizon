## Why

Blog posts published to Webflow currently have no author assigned, leaving all posts authorless. Multiple authors exist in Webflow and each post should be attributed to one, chosen at random per post to distribute authorship across the team.

## What Changes

- Add `authors_collection_id` and `author_field` config fields to `PublisherConfig`
- Add a method to `WebflowPublisher` to fetch all items from the Authors collection
- Randomly assign one author per post before pushing to Webflow
- Author assignment is fail-open: if no authors are found or the fetch fails, posts publish without an author

## Capabilities

### New Capabilities

- `webflow-author-assignment`: Fetch all authors from Webflow's Authors collection and randomly assign one author reference per published blog post

### Modified Capabilities

<!-- None — no existing spec-level requirements are changing -->

## Impact

- `src/blog/models.py` — `PublisherConfig` gains two new optional fields
- `src/blog/publisher/webflow.py` — `WebflowPublisher.__init__` gains `author_field` param; new `list_authors()` method added; `add_draft()` reads `author_id` from the post dict
- `src/blog/publisher/runner.py` — fetches authors once at run start; assigns a random author ID to each post dict before calling `add_draft`
- `data/config.json` — two new publisher config keys to document
