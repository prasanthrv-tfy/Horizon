## 1. Extend BlogPromptProfile

- [x] 1.1 Add optional `ranking_context: str = ""` field to `BlogPromptProfile` in `src/blog/profiles/profile.py`
- [x] 1.2 Add a `ranking_context` value to the `practitioner` profile in `src/blog/profiles/practitioner.py` — 2–4 sentences describing what makes an item relevant for ML engineers (paper/repo/benchmark present, concrete engineering implication, changes how models are built or served)
- [x] 1.3 Add a `ranking_context` value to the `journalist` profile in `src/blog/profiles/journalist.py` — 2–4 sentences describing what makes an item relevant for general tech readers (broad impact, clear narrative, newsworthiness)

## 2. Update Ranking Prompt

- [x] 2.1 Add an `{audience_context}` placeholder to `RELEVANCE_RANKING_SYSTEM` in `src/blog/prompts.py` — insert it as a conditional block that, when non-empty, instructs the LLM to rank by the provided audience criteria instead of generic newsworthiness
- [x] 2.2 Update `RELEVANCE_RANKING_USER` (if needed) to pass through any profile-specific context

## 3. Make Runner Profile-Aware

- [x] 3.1 Add `audience_context: str = ""` parameter to `rank_by_relevance()` in `src/blog/runner.py` and format it into the ranking prompt
- [x] 3.2 Remove the single `rank_by_relevance()` call that runs before the profile loop
- [x] 3.3 Inside the profile loop (before `generate_and_save_posts`), call `rank_by_relevance(items, ai_client, console, profile.ranking_context)` and slice to `max_posts`
- [x] 3.4 Add a console log line after ranking that lists the selected item titles for that profile, so users can see which items each profile chose

## 4. Verify

- [x] 4.1 Run `uv run horizon-blog --profile practitioner` and confirm the selected items differ in character from a journalist run (technical depth vs broad impact)
- [x] 4.2 Run `uv run horizon-blog --profile all` and confirm both profiles complete without error and may select different items
- [x] 4.3 Confirm that a profile with empty `ranking_context` still runs without error (generic fallback)
