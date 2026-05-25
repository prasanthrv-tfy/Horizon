## Why

The blog runner currently selects items by ranked order alone — the top N always get posts regardless of actual relevance to the profile audience. For TrueFoundry's practitioner audience (ML engineers deploying, serving, and fine-tuning models), this produces posts about Google I/O roundups and business partnerships that engineers have no reason to read.

## What Changes

- **BREAKING**: Replace `rank_by_relevance()` with a new `score_items_for_profile()` function. Items are scored on multiple dimensions with per-dimension reasons, filtered by profile-defined gate paths, and ranked by weighted sum within included items.
- Add `ScoringDimension` dataclass to `src/blog/models.py`: name, description, gate threshold, per-path weight, and scale anchors.
- Add `scoring_dimensions` and `gate_paths` fields to `BlogPromptProfile`. Each profile defines its own dimensions, thresholds, and inclusion paths.
- Define four dimensions for the practitioner profile: `ml_engineering_relevance`, `technical_substance`, `production_applicability`, `ai_ecosystem_significance` — with two inclusion paths (technical depth OR ecosystem event).
- Define three dimensions for the journalist profile: `significance`, `newsworthiness`, `narrative_clarity`.
- Add a new scoring prompt to `src/blog/prompts.py` that requests per-dimension scores and reasons in one LLM call.
- Write a JSON run log to `data/blog-runs/YYYY-MM-DD-{profile}.json` after each run, containing full scoring details for every evaluated item.
- Console output shows a per-item dimension table with scores, reasons, path pass/fail, weighted sum, and include/exclude decision.
- Zero posts is a valid outcome if no items pass the gates for a profile.

## Capabilities

### New Capabilities

- `multi-dimensional-scoring`: Per-profile scoring of candidate items across named dimensions, gate-based include/exclude logic with two OR paths, per-path weighted sum computation, and JSON run log persistence.

### Modified Capabilities

- `profile-aware-ranking`: The ranking capability is superseded by scoring. Items are no longer just ordered — they are scored, gated, and ranked by weighted sum. The `ranking_context` field is replaced by `scoring_dimensions` and `gate_paths`.
- `blog-generation`: Item selection now produces zero or more posts depending on gate results, rather than always selecting exactly top-N items.

## Impact

- `src/blog/models.py`: new `ScoringDimension` dataclass, new `ScoredItem` dataclass
- `src/blog/profiles/profile.py`: new `scoring_dimensions` and `gate_paths` fields replacing `ranking_context`
- `src/blog/profiles/practitioner.py`: four dimensions + two gate paths defined
- `src/blog/profiles/journalist.py`: three dimensions + one gate path defined
- `src/blog/prompts.py`: new `ITEM_SCORING_SYSTEM` and `ITEM_SCORING_USER` prompts; old ranking prompts retained for backwards compat but no longer called
- `src/blog/runner.py`: `rank_by_relevance()` replaced by `score_items_for_profile()`; runner writes run log
- `data/blog-runs/`: new directory, gitignored like `data/pipeline-output/`
