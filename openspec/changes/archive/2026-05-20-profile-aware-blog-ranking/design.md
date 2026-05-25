## Context

`src/blog/runner.py` currently calls `rank_by_relevance()` once before the profile loop, then slices `items[:max_posts]` and passes the same list to every profile's `generate_and_save_posts()`. The ranking prompt (`RELEVANCE_RANKING_SYSTEM`) uses generic criteria — newsworthiness, breadth of impact, timeliness — with no awareness of the intended audience.

`BlogPromptProfile` already carries rich audience descriptions in `blog_system`, but those are only used at the writing stage. Nothing in the selection path uses them.

## Goals / Non-Goals

**Goals:**
- Each profile ranks and selects items independently using audience-specific criteria.
- Practitioner profile surfaces items with papers, benchmarks, repos, or concrete engineering implications over broad product announcements.
- Minimal code surface change — no new dependencies, no pipeline changes.

**Non-Goals:**
- Making the upstream pipeline scorer profile-aware (separate future work).
- Changing how profiles write posts once items are selected.
- Adding per-profile config for `max_posts`.

## Decisions

### 1. Add `ranking_context` field to `BlogPromptProfile`

Each profile defines a short (2–4 sentence) description of what makes a news item relevant *for ranking purposes*. This is separate from `blog_system` (which is long and writing-focused) — the ranking context needs to be concise enough to fit cleanly into a ranking prompt without noise.

**Alternative considered**: Extract audience description from `blog_system` via prompt or regex. Rejected — `blog_system` is a full writing instruction, not a clean audience summary. Parsing it reliably is fragile.

**Alternative considered**: Pass the full `blog_system` into the ranking prompt. Rejected — it is 600+ words of writing instructions; injecting it into a ranking prompt would dilute the ranking signal.

### 2. Move `rank_by_relevance()` inside the profile loop

```
# Before
items = await rank_by_relevance(items, ai_client, console)
items = items[:max_posts]
for profile in profiles:
    await generate_and_save_posts(items, config, profile, console)

# After
for profile in profiles:
    ranked = await rank_by_relevance(items, ai_client, console, profile.ranking_context)
    selected = ranked[:max_posts]
    await generate_and_save_posts(selected, config, profile, console)
```

**Alternative considered**: Keep ranking outside the loop and pass profile context as a separate re-rank pass. Rejected — two ranking passes adds latency with no benefit; a single profile-aware pass is cleaner.

### 3. Update `RELEVANCE_RANKING_SYSTEM` with an injected audience block

Add a placeholder `{audience_context}` that is formatted in when a profile provides ranking context, and omitted (or replaced with a neutral fallback) when none is provided. This keeps the prompt backward-compatible if `ranking_context` is empty.

## Risks / Trade-offs

- **Latency increase**: Ranking now runs once per profile instead of once total. With the default `max_posts=4` and 2 profiles, this doubles ranking API calls. Acceptable given ranking is a single lightweight call. → No mitigation needed at current scale.
- **Different profiles, different posts**: The same pipeline run may produce posts about entirely different items per profile. This is the intended behavior but may surprise users who expect profiles to be style variants of the same content. → Document clearly in the runner's console output which items each profile selected.
- **ranking_context left empty**: If a new profile is added without a `ranking_context`, the prompt falls back to generic criteria — same behavior as today, no regression. → Low risk.

## Open Questions

- Should `ranking_context` be optional (defaulting to the generic criteria) or required on `BlogPromptProfile`? Leaning optional to avoid breaking existing profiles during the migration.
