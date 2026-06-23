## Why

Blog posts published to Webflow currently have no category assigned. A categories collection exists in Webflow with a reference field `category-2` on the blog collection, and matching an article to the right category requires intelligence — the best category is chosen by an LLM comparing article title and tags against available category names.

## What Changes

- Add `categories_collection_id` and `category_field` config fields to `PublisherConfig`
- Add a new `category.py` module with `assign_category()` — an LLM call that picks the best-matching category name from the available list and returns its Webflow ID
- Add `list_categories()` method to `WebflowPublisher` for fetching the categories collection
- Fetch categories once at run start; per post, call `assign_category()` and set the result on the post before pushing to Webflow
- Category assignment is fail-open: if the collection is empty, fetch fails, or the LLM returns no match, posts publish without a category

## Capabilities

### New Capabilities

- `webflow-category-assignment`: Fetch all categories from Webflow's Categories collection and use an LLM to assign the most relevant category to each published blog post based on its title and tags

### Modified Capabilities

<!-- None — no existing spec-level requirements are changing -->

## Impact

- `src/blog/models.py` — `PublisherConfig` gains two new optional fields
- `src/blog/publisher/category.py` — new module; `assign_category()` function
- `src/blog/publisher/webflow.py` — `WebflowPublisher.__init__` gains `category_field` param; new `list_categories()` method; `add_draft()` reads `category_id` from post dict
- `src/blog/publisher/__init__.py` — passes `category_field` when constructing `WebflowPublisher`
- `src/blog/publisher/runner.py` — fetches categories at run start; calls `assign_category()` per post
- `data/config.json` — two new publisher config keys to document