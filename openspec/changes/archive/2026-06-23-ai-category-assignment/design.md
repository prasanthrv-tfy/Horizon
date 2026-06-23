## Context

The Webflow publisher pushes blog posts to a CMS collection via the Staged Items API. The blog collection has a `category-2` reference field pointing to a separate Webflow Categories collection. Posts currently publish without this field set. Category assignment can't be random (unlike authors) — it requires reasoning about article content to find a semantically appropriate match from the available options.

The pipeline already has an AI client (`ai_client`) available in `runner.py` and uses it per-post for SEO generation (`seo.py`). The `seo.py` module is the closest analogue: one LLM call per post, system prompt + user template, JSON response, fail open on error.

## Goals / Non-Goals

**Goals:**
- Fetch all categories from the Webflow Categories collection once per publish run
- For each post, use an LLM to identify the most relevant category by comparing article title and tags against available category names
- Set `field_data["category-2"]` to the matched category's Webflow item ID
- Fail open at every step: empty collection, fetch error, LLM error, or no match → post publishes without a category

**Non-Goals:**
- Multi-category assignment (single best match only)
- Caching categories across runs
- Falling back to source `category` field on `ContentItem` (would need mapping logic; not worth the complexity)

## Decisions

### 1. New `category.py` module, not inline in `runner.py`

Category assignment is a distinct concern with its own prompt and parsing logic. Keeping it in `category.py` mirrors `seo.py` and keeps `runner.py` as an orchestrator. The function signature is `assign_category(title, tags, categories, ai_client) -> Optional[str]`.

### 2. LLM reasons over names, returns a name, caller does ID lookup

Asking the LLM to return a Webflow item ID directly is fragile — IDs are opaque strings the model can't reason about. Instead, the prompt presents human-readable category names and asks the model to return the single best-matching name. `assign_category` then does a name → ID lookup from the pre-built map.

**Alternative considered**: ask the LLM to return a JSON object with `{"category": "<name>"}` — adopted, mirrors `seo.py`'s JSON pattern and is easier to parse reliably than free text.

### 3. Categories fetched once per run, shared across all posts

Same rationale as `list_authors`: the categories collection changes rarely, one fetch is sufficient, and reusing the in-memory list avoids N redundant API calls.

### 4. `list_categories` follows the exact same pattern as `list_authors`

Reusing the same pagination loop and error handling keeps the codebase consistent. Both methods accept a collection ID as a parameter (not stored on `self`).

### 5. `category_field` configurable, defaulting to `"category-2"`

The Webflow field slug is known to be `"category-2"`, but making it configurable costs nothing and avoids a code change if it ever changes.

## Risks / Trade-offs

- **LLM picks a category that doesn't exist** → name lookup returns None → post publishes without category. Acceptable; categories collection is empty at launch anyway.
- **Categories collection is empty** → warning logged, run continues without assignment. This is the expected state at deploy time.
- **LLM latency per post** → `assign_category` adds one AI call per post, same as SEO generation. Both calls happen sequentially per post; no change to concurrency model.
- **Category names change in Webflow** → stale name in LLM response won't match the lookup map → silently skips category. Mitigation: categories fetched fresh each run.

## Migration Plan

1. Add `categories_collection_id` and `category_field` to `PublisherConfig` with empty/default values — fully backward compatible; existing runs without config set behave identically to today.
2. Deploy code.
3. Populate the Webflow Categories collection.
4. Set `categories_collection_id` in `data/config.json` to activate.

No rollback concern — empty `categories_collection_id` is a no-op.