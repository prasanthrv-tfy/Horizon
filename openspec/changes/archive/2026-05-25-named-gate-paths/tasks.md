## 1. Data Model

- [x] 1.1 Add `PathDimensionConfig` dataclass to `src/blog/models.py` with fields `dimension: str`, `weight: float`, `threshold: float`
- [x] 1.2 Add `GatePath` dataclass to `src/blog/models.py` with fields `name: str`, `dimensions: List[PathDimensionConfig]`
- [x] 1.3 Slim `ScoringDimension` — remove `gate_threshold`, `path_a_weight`, `path_b_weight`, `path_c_weight`, `path_thresholds` fields
- [x] 1.4 Update `BlogPromptProfile.gate_paths` type annotation from `List[List[str]]` to `List[GatePath]` in `src/blog/profiles/profile.py`

## 2. Runner Logic

- [x] 2.1 Rewrite `_compute_weighted_sum` in `runner.py` to accept a `GatePath` and compute `Σ(pdc.weight × score)` over `gate_path.dimensions`
- [x] 2.2 Rewrite the gate evaluation loop in `score_items_for_profile` to iterate `GatePath` objects (using `gate_path.name` instead of `chr(ord("A") + idx)` labels, and `pdc.threshold` instead of `d.path_thresholds.get(label, d.gate_threshold)`)
- [x] 2.3 Update excluded-item best-possible-sum computation to call `_compute_weighted_sum` over each `GatePath`
- [x] 2.4 Update the dimensions prompt text assembly in `score_items_for_profile` — remove the `Gate threshold: {d.gate_threshold}` line since thresholds now live on paths

## 3. Practitioner Profile

- [x] 3.1 Remove Path A (`["ml_engineering_relevance", "technical_substance"]`) from `gate_paths`
- [x] 3.2 Define `GatePath(name="production_ready", dimensions=[...])` with the four dimensions from former Path B (ml_engineering_relevance, technical_substance, production_applicability, ai_ecosystem_significance) using their former Path B weights and thresholds
- [x] 3.3 Define `GatePath(name="research_significance", dimensions=[...])` with three dimensions (ml_engineering_relevance, technical_substance, engineering_insight) using their former Path C weights and thresholds
- [x] 3.4 Remove `path_a_weight`, `path_b_weight`, `path_c_weight`, `path_thresholds`, `gate_threshold` from all `ScoringDimension` entries in `practitioner.py`

## 4. Journalist Profile

- [x] 4.1 Wrap the journalist profile's single path in `GatePath(name="editorial", dimensions=[...])` using former `gate_threshold` values as `PathDimensionConfig.threshold` and `path_a_weight` values as `weight`
- [x] 4.2 Remove `path_a_weight`, `path_b_weight`, `gate_threshold` from all `ScoringDimension` entries in `journalist.py`

## 5. Output and Docs

- [x] 5.1 Verify ranking table console output and `artifacts/ranking_results.md` generation show path names (e.g. `production_ready`) not letters — fix any hardcoded label references in the table-rendering code in `runner.py`
- [x] 5.2 Update `docs/blog-profiles.md` — replace Path A/B/C table with `production_ready` / `research_significance` named path descriptions, update the gate path dimension tables with thresholds and weights

## 6. Verification

- [x] 6.1 Run `uv run horizon-blog --rank-only` and confirm output shows named paths (`production_ready`, `research_significance`) with the same 17 included items as the May 25 run
- [x] 6.2 Confirm no references to `path_a_weight`, `path_b_weight`, `path_c_weight`, `path_thresholds`, or `chr(ord("A")` remain in `src/blog/`
