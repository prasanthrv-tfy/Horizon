## Why

The blog scoring pipeline is making filtering decisions on RSS excerpts of 100–200 characters. Most items have content that is just one or two teaser sentences — the full article body is never fetched. This means the LLM scorer is effectively working from the title alone, causing items like GPT-Rosalind (no architecture details in the excerpt, full blog post has more) to score `technical_substance=4` and be excluded, and items with richer downstream pages to be mis-scored in either direction.

The upstream Horizon scraper is intentionally left untouched (upstream sync compatibility). The fix belongs entirely in the blog module, as a pre-scoring enrichment step.

## What Changes

- **New `src/blog/fetcher.py`**: `ContentFetcher` class with two strategies:
  1. `fetch_url(url)` — HTTP GET of the item's URL, strips HTML to plain text, returns first 2000 chars.
  2. `search_fallback(title, tags)` — DuckDuckGo search using title + tags as the query, returns a concatenated snippet of the top results.
- **`src/blog/runner.py`**: A new `enrich_thin_items()` async function runs before `score_items_for_profile()`. For each item where `len(item.content or "") < 500`, it attempts `fetch_url` first, then `search_fallback` if the fetch fails or returns too little text. Enriched content is written back to `item.content` in-memory only — not persisted to `important_items.json`.
- **`src/blog/runner.py`**: Increase the content preview window in `_score_single_item` from 400 to 1500 characters so the scorer can actually use the enriched content.

## Capabilities

### New Capabilities

- `blog-content-prefetch`: Before scoring, items with thin content (< 500 chars) are enriched by fetching the source URL or falling back to a search query. Enrichment is in-memory and transparent to the rest of the pipeline.

### Modified Capabilities

- `multi-dimensional-scoring`: Scorer now receives up to 1500 chars of content per item instead of 400. No change to scoring logic or prompts.

## Impact

- `src/blog/fetcher.py` — new file (~80 lines)
- `src/blog/runner.py` — `enrich_thin_items()` added, `_score_single_item` content slice widened
- No changes to `src/blog/profiles/`, `src/blog/models.py`, `src/blog/prompts.py`, `src/blog/writer.py`, or any upstream Horizon file
