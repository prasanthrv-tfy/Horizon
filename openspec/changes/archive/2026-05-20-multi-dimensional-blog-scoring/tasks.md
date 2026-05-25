## 1. Data Models

- [x] 1.1 Add `ScoringDimension` dataclass to `src/blog/models.py` with fields: `name: str`, `description: str`, `gate_threshold: float`, `path_a_weight: float`, `path_b_weight: float`, `anchors: dict[str, str]`
- [x] 1.2 Add `ScoredItem` dataclass to `src/blog/models.py` with fields: `item: ContentItem`, `dimension_scores: dict[str, dict]` (maps dimension name → {score, reason}), `path_results: dict[str, dict]`, `included: bool`, `inclusion_path: str | None`, `failed_gates: dict[str, list[str]]`, `weighted_sum: float`
- [x] 1.3 Add `scoring_dimensions: List[ScoringDimension]` and `gate_paths: List[List[str]]` fields (both defaulting to empty list) to `BlogPromptProfile` in `src/blog/profiles/profile.py`
- [x] 1.4 Mark `ranking_context` as deprecated in `BlogPromptProfile` docstring (retain field, do not remove)

## 2. Scoring Prompt

- [x] 2.1 Add `ITEM_SCORING_SYSTEM` prompt to `src/blog/prompts.py` — instructs the LLM to score all items on the provided dimensions, return JSON with per-item per-dimension `{score, reason}`, and use the dimension anchors to calibrate the 0-10 scale
- [x] 2.2 Add `ITEM_SCORING_USER` prompt to `src/blog/prompts.py` — formats items list, dimension definitions with anchors, and requests JSON response: `{"items": [{"id": "...", "dimensions": {"dim_name": {"score": N, "reason": "..."}}}]}`

## 3. Practitioner Profile Dimensions

- [x] 3.1 Define `ml_engineering_relevance` `ScoringDimension` in `src/blog/profiles/practitioner.py`: gate_threshold=6, path_a_weight=0.45, path_b_weight=0.0, anchors for 1/5/8/10
- [x] 3.2 Define `technical_substance` `ScoringDimension`: gate_threshold=5, path_a_weight=0.35, path_b_weight=0.0, anchors describing paper/repo/benchmark presence
- [x] 3.3 Define `production_applicability` `ScoringDimension`: gate_threshold=4 (Path A) / 5 (Path B — use the stricter value as gate_threshold), path_a_weight=0.20, path_b_weight=0.40, anchors describing deployability today
- [x] 3.4 Define `ai_ecosystem_significance` `ScoringDimension`: gate_threshold=7, path_a_weight=0.0, path_b_weight=0.60, anchors describing flagship vs minor model releases
- [x] 3.5 Set `gate_paths` on practitioner profile: `[["ml_engineering_relevance", "technical_substance", "production_applicability"], ["ai_ecosystem_significance", "production_applicability"]]`
- [x] 3.6 Remove `ranking_context` value from practitioner profile (field stays, value set to empty string)

## 4. Journalist Profile Dimensions

- [x] 4.1 Define `significance` `ScoringDimension` for journalist: gate_threshold=6, path_a_weight=0.45, anchors describing broad societal/industry impact
- [x] 4.2 Define `newsworthiness` `ScoringDimension`: gate_threshold=5, path_a_weight=0.35, anchors describing timeliness and originality
- [x] 4.3 Define `narrative_clarity` `ScoringDimension`: gate_threshold=4, path_a_weight=0.20, anchors describing how clearly a non-expert story can be told
- [x] 4.4 Set `gate_paths` on journalist profile: `[["significance", "newsworthiness", "narrative_clarity"]]` (single path)
- [x] 4.5 Remove `ranking_context` value from journalist profile (field stays, value set to empty string)

## 5. Scoring Function

- [x] 5.1 Add `score_items_for_profile(items, ai_client, console, profile)` async function to `src/blog/runner.py` — assembles the scoring prompt with dimension definitions and anchors, calls the AI client, parses the JSON response into `ScoredItem` objects
- [x] 5.2 Implement gate evaluation in `score_items_for_profile()` — for each item, check each gate path (AND within path), mark included if any path passes (OR across paths), record `inclusion_path` and `failed_gates`
- [x] 5.3 Implement per-path weighted sum computation — Path A sum uses `path_a_weight`, Path B sum uses `path_b_weight`; `weighted_sum = max(path_a_sum, path_b_sum)` across passing paths
- [x] 5.4 Implement console table output in `score_items_for_profile()` — one row per item showing title (truncated), per-dimension scores, weighted sum, and decision (✓ Path A / ✓ Path B / ✗ + failed gates)
- [x] 5.5 Implement run log writer — after scoring, write `data/blog-runs/YYYY-MM-DD-{profile}.json` with full `ScoredItem` details for all evaluated items

## 6. Runner Integration

- [x] 6.1 Update `_run()` in `src/blog/runner.py` — inside the profile loop, if `profile.scoring_dimensions` is non-empty call `score_items_for_profile()` and filter to included items; otherwise fall back to existing `rank_by_relevance()` + slice
- [x] 6.2 Sort included items by `weighted_sum` descending before applying `max_posts` cap
- [x] 6.3 Pass included `ContentItem` objects (not `ScoredItem`) to `generate_and_save_posts()` — extract `.item` from each `ScoredItem`
- [x] 6.4 Ensure `data/blog-runs/` directory is created if it does not exist; add it to `.gitignore`

## 7. Verify

- [x] 7.1 Run `uv run horizon-blog --profile practitioner` — confirm scoring table appears in console, run log written to `data/blog-runs/`, and only gate-passing items get posts
- [x] 7.2 Run `uv run horizon-blog --profile all` — confirm journalist and practitioner may select different items, both run logs written
- [x] 7.3 Inspect run log JSON — confirm all fields present: dimension scores, reasons, path results, weighted_sum, inclusion_path, failed_gates
- [x] 7.4 Confirm zero-post scenario is handled cleanly (manually set thresholds high, verify no crash and clear console message)
