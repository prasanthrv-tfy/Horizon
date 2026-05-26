## Context

The publisher (`src/blog/publisher/`) pushes generated blog posts to Webflow. Before publishing, it deduplicates against existing Webflow items using normalised exact-title matching (`deduplicator.py`). This misses semantically identical stories with differently-worded headlines (e.g., same announcement covered by AWS blog vs TechCrunch on different days).

The AI client (`ai_client`) is already instantiated in `runner.py` and used for SEO generation — it is available at no additional wiring cost.

## Goals / Non-Goals

**Goals:**
- Catch semantic duplicate posts that survive the normalised title match
- Keep LLM calls minimal: only check posts that are candidates to publish, stop when limit is reached
- Distinguish title-match skips from semantic-match skips in output

**Non-Goals:**
- Cross-run dedup using URL or other metadata (deferred to later)
- Dedup within the local `kept` list (upstream pipeline already handles this)
- Retrying failed semantic checks

## Decisions

**Decision: Lazy evaluation inside the publish loop (not a pre-filter pass)**

The semantic check runs one-by-one inside the existing publish loop, immediately before `publisher.add_draft`. A post is only checked if the publish limit hasn't been reached. This means zero extra LLM calls for posts that would never have been published anyway.

Alternative considered: a separate pre-filter pass over all `kept` items. Rejected because it would call the LLM for items beyond the publish limit unnecessarily.

**Decision: Fail open on semantic check errors**

If the LLM call for semantic dedup fails (network error, malformed response), the post is treated as NOT a duplicate and is published. This is safer than blocking publication on a transient AI failure.

**Decision: Pass all existing Webflow titles in a single prompt**

Rather than one LLM call per (new post, existing post) pair, we send all existing titles in one call and ask "does this new title cover the same story as any of these?". This keeps the check to a single call per candidate.

**Decision: JSON response format**

The prompt requests `{"is_duplicate": bool, "matched_title": str | null}` for easy parsing. If JSON parsing fails, fall back to treating it as not a duplicate (fail open).

## Risks / Trade-offs

- **LLM cost per publish run**: Each candidate post beyond title-match dedup costs one LLM call. With a typical `max_drafts` of 4–5 and most posts already caught by title match, this is 1–3 extra calls per run. Acceptable.
- **Existing titles list length**: The Webflow `list_items` call is already time-windowed (`deduplication_time_window`, default 14 days). The title list passed to the LLM is bounded by that window.
- **False positives**: LLM may flag genuinely different posts as duplicates if headlines overlap (e.g., two separate GPT-4 update posts). Threshold is in the prompt wording ("covers the exact same news event or announcement").

## Open Questions

- None. Design is fully resolved for this scope.
