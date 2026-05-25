## Why

The blog re-ranking step in `src/blog/runner.py` runs once with a generic prompt before the profile loop, so every profile receives the same ranked item list. This means the practitioner profile's ranking is driven by criteria like "breadth of impact" and "newsworthiness" that consistently surface high-visibility product launches and policy roundups over technically-deep content that ML engineers actually care about.

## What Changes

- Move `rank_by_relevance()` inside the profile loop so each profile ranks items independently.
- Add an `audience_context` parameter to `rank_by_relevance()` that is injected into the ranking prompt.
- Update `RELEVANCE_RANKING_SYSTEM` in `src/blog/prompts.py` to accept and apply profile-specific audience context when ranking.
- Each profile supplies its own audience description (already defined in `blog_system`) so the ranking criteria shift per audience — e.g., practitioner ranking weights paper/repo/benchmark presence over newsworthiness.

## Capabilities

### New Capabilities

- `profile-aware-ranking`: Each blog profile ranks the candidate item pool independently using its own audience context, producing a different top-N selection per profile.

### Modified Capabilities

- `blog-generation`: The runner's item selection step now runs per-profile rather than once globally. Behavior change: different profiles may generate posts about different items from the same pipeline output.

## Impact

- `src/blog/runner.py`: structural change to move ranking inside the profile loop; pass profile context into `rank_by_relevance`.
- `src/blog/prompts.py`: update `RELEVANCE_RANKING_SYSTEM` to accept an audience context block.
- `src/blog/profiles/profile.py`: may need a new `ranking_context` field on `BlogPromptProfile` to carry a concise ranking description distinct from the full `blog_system` prompt.
- No changes to pipeline, scrapers, models, or other modules.
