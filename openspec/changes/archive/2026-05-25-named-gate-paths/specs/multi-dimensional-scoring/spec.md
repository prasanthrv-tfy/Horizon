## MODIFIED Requirements

### Requirement: ScoringDimension defines a named scoring axis
A `ScoringDimension` dataclass SHALL exist in `src/blog/models.py` with fields: `name: str`, `description: str`, and `anchors: dict[str, str]` (maps score string values to human-readable descriptions for LLM calibration). It SHALL NOT have `gate_threshold`, `path_a_weight`, `path_b_weight`, `path_c_weight`, or `path_thresholds` fields — all weight and threshold information lives in `PathDimensionConfig` on the `GatePath`.

#### Scenario: ScoringDimension instantiated with only scoring-axis fields
- **WHEN** a `ScoringDimension` is created with name, description, and anchors
- **THEN** all fields are accessible and the object is usable as a profile dimension

#### Scenario: Anchors guide LLM calibration
- **WHEN** the scoring prompt is assembled
- **THEN** each dimension's anchors are included in the prompt to ground the 0-10 scale

---

### Requirement: ScoredItem carries per-dimension scores and gate results
A `ScoredItem` dataclass SHALL exist in `src/blog/models.py` with fields: `item` (the original `ContentItem`), `dimension_scores: dict[str, dict]`, `path_results: dict[str, dict]` (keyed by gate path name, not letter), `inclusion_path: Optional[str]` (gate path name or None), `failed_gates: dict[str, list[str]]`, and `weighted_sum: float`.

#### Scenario: ScoredItem populated after scoring
- **WHEN** `score_items_for_profile()` processes an item
- **THEN** the returned `ScoredItem` has dimension scores for each dimension, path_results keyed by path name, and gate results reflecting pass/fail per path

---

### Requirement: BlogPromptProfile carries scoring_dimensions and gate_paths
`BlogPromptProfile` SHALL include `scoring_dimensions: List[ScoringDimension]` (default empty list) and `gate_paths: List[GatePath]` (default empty list). Each `GatePath` owns its name, the dimensions it gates on, and each dimension's threshold and weight. An item is included if ANY gate path passes (all its dimensions meet their thresholds).

#### Scenario: Profile with scoring_dimensions defined
- **WHEN** a `BlogPromptProfile` is instantiated with non-empty `scoring_dimensions` and `gate_paths`
- **THEN** those fields are accessible and used by the scoring function

#### Scenario: Profile with no scoring_dimensions falls back to ranking
- **WHEN** a `BlogPromptProfile` has empty `scoring_dimensions`
- **THEN** the runner falls back to `rank_by_relevance()` behavior (backwards compatibility)

---

### Requirement: score_items_for_profile scores all items in one LLM call
The `score_items_for_profile()` function SHALL send all candidate items to the LLM in a single call, receiving back a score (0-10) and a reason for each dimension for each item.

#### Scenario: All items scored in one call
- **WHEN** `score_items_for_profile()` is called with N items and a profile with M dimensions
- **THEN** the LLM returns N × M dimension scores each with a reason, in a single API call

#### Scenario: LLM scoring failure falls back to rank order
- **WHEN** the LLM call fails or returns unparseable JSON
- **THEN** a warning is logged and items fall back to their original order with no gate filtering applied

---

### Requirement: Gate paths determine inclusion via AND within path, OR across paths
An item SHALL be included if at least one `GatePath` has all its `PathDimensionConfig` entries scoring at or above their individual thresholds. Items failing all gate paths are excluded.

#### Scenario: Item passes production_ready path
- **WHEN** an item scores >= threshold on all dimensions in the `production_ready` GatePath
- **THEN** the item is included and `inclusion_path` is set to `"production_ready"`

#### Scenario: Item passes research_significance path
- **WHEN** an item fails `production_ready` but scores >= threshold on all dimensions in `research_significance`
- **THEN** the item is included and `inclusion_path` is set to `"research_significance"`

#### Scenario: Item fails all paths
- **WHEN** an item fails to meet threshold on at least one dimension in every gate path
- **THEN** the item is excluded and `failed_gates` lists the failing dimensions per path

#### Scenario: Zero items pass
- **WHEN** all items fail all gate paths
- **THEN** no blog posts are generated for that profile and the runner logs a clear message

---

### Requirement: Per-path weighted sum ranks included items
For each included item, the weighted sum SHALL be computed using the winning `GatePath`'s `PathDimensionConfig` entries: `Σ(pdc.weight × score)`. Dimensions present in `scoring_dimensions` but absent from the winning path contribute 0 to that path's weighted sum.

#### Scenario: production_ready item weighted sum uses that path's weights
- **WHEN** an item is included via `production_ready`
- **THEN** `weighted_sum = Σ(pdc.weight × score)` for each `PathDimensionConfig` in the `production_ready` GatePath

#### Scenario: Excluded item gets best possible sum for reference
- **WHEN** an item fails all gate paths
- **THEN** `weighted_sum` is the maximum weighted sum across all paths (using each path's own weights), for display in the ranking table
