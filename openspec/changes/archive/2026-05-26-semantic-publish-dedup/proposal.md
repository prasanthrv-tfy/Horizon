## Why

The publisher's deduplication currently does a normalised exact-title match against existing Webflow items. This misses cases where the same story is covered by a different source on a different day with a differently-worded headline (e.g., "OpenAI releases GPT-5" vs "GPT-5 is here: OpenAI's latest model"). Those slip through as duplicate articles.

## What Changes

- **Two-pass deduplication in the publish loop**: the existing normalised title match runs first as a fast pre-filter. Items that survive it are then checked one-by-one with an LLM semantic similarity call against the full set of existing Webflow titles before being published.
- The LLM check is done lazily inside the publish loop — a post is only checked if it hasn't been eliminated by title match and the publish limit hasn't yet been reached. This keeps LLM calls to a minimum.
- Add a `semantic_is_duplicate(title, existing_titles, ai_client)` async function to `deduplicator.py` that returns `(is_dup: bool, matched_title: str | None)`.
- Update `runner.py`'s publish loop to call `semantic_is_duplicate` for each candidate before calling `publisher.add_draft`. Posts identified as semantic duplicates are counted in the skipped summary with a `[semantic]` tag.
- No new config keys required; the feature is always on when the AI client is available (which it always is in the runner).

## Capabilities

### Modified Capabilities

- `publish-deduplication`: Extended from exact normalised-title match to a two-pass pipeline: (1) fast exact match, (2) LLM semantic match for survivors, evaluated lazily one-by-one until the publish limit is reached.

## Impact

- `src/blog/publisher/deduplicator.py`: add `semantic_is_duplicate(title, existing_titles, ai_client)` async function and a dedicated prompt
- `src/blog/publisher/runner.py`: publish loop calls `semantic_is_duplicate` per candidate; skipped-summary output distinguishes title-match vs semantic-match skips
