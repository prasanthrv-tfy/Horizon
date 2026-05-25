# Multi-Dimensional Blog Scoring Spec

## Requirements

### Requirement: ScoringDimension defines a named scoring axis
A `ScoringDimension` dataclass SHALL exist in `src/blog/models.py` with fields: `name: str`, `description: str`, `gate_threshold: float`, `path_a_weight: float`, `path_b_weight: float`, and `anchors: dict[str, str]` (maps score values to human-readable descriptions for LLM calibration).

#### Scenario: ScoringDimension instantiated with all fields
- **WHEN** a `ScoringDimension` is created with name, description, threshold, weights, and anchors
- **THEN** all fields are accessible and the object is usable as a profile dimension

#### Scenario: Anchors guide LLM calibration
- **WHEN** the scoring prompt is assembled
- **THEN** each dimension's anchors are included in the prompt to ground the 0-10 scale

---

### Requirement: ScoredItem carries per-dimension scores and gate results
A `ScoredItem` dataclass SHALL exist in `src/blog/models.py` with fields: `item` (the original `ContentItem`), `dimension_scores: dict[str, float]`, `dimension_reasons: dict[str, str]`, `inclusion_path: Optional[str]`, `failed_gates: dict[str, list[str]]`, and `weighted_sum: float`.

#### Scenario: ScoredItem populated after scoring
- **WHEN** `score_items_for_profile()` processes an item
- **THEN** the returned `ScoredItem` has dimension scores and reasons for each dimension, and gate results reflecting pass/fail per path

---

### Requirement: BlogPromptProfile carries scoring_dimensions and gate_paths
`BlogPromptProfile` SHALL include `scoring_dimensions: List[ScoringDimension]` (default empty list) and `gate_paths: List[List[str]]` (default empty list). Each gate path is a list of dimension names that must ALL pass their thresholds. An item is included if ANY gate path passes.

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
An item SHALL be included if at least one gate path has all its referenced dimensions scoring at or above their `gate_threshold`. Items failing all gate paths are excluded.

#### Scenario: Item passes Path A (research awareness)
- **WHEN** an item scores >= threshold on all dimensions in Path A (ml_engineering_relevance and technical_substance, no production_applicability gate)
- **THEN** the item is included, `inclusion_path` is set to "A"

#### Scenario: Item passes Path B (production ready)
- **WHEN** an item fails Path A but scores >= threshold on all dimensions in Path B (ml_engineering_relevance, technical_substance, and production_applicability)
- **THEN** the item is included, `inclusion_path` is set to "B"

#### Scenario: Item fails all paths
- **WHEN** an item fails to meet threshold on at least one dimension in every gate path
- **THEN** the item is excluded and `failed_gates` lists the failing dimensions per path

#### Scenario: Zero items pass
- **WHEN** all items fail all gate paths
- **THEN** no blog posts are generated for that profile and the runner logs a clear message

---

### Requirement: Per-path weighted sum ranks included items
For each included item, the weighted sum SHALL be computed per path using the path's dimensions and their `path_a_weight` or `path_b_weight` values. The item's final `weighted_sum` is the maximum across all paths it could satisfy. Dimensions not used in a given path (weight = 0) SHALL still be scored but SHALL NOT contribute to that path's weighted sum.

#### Scenario: Path A item weighted sum uses only Path A dimensions
- **WHEN** an item is included via Path A
- **THEN** `weighted_sum = Σ(dimension.path_a_weight × score)` for dimensions with non-zero path_a_weight only

#### Scenario: Path B item weighted sum uses all Path B dimensions including ranking-only dimensions
- **WHEN** an item is included via Path B
- **THEN** `weighted_sum = Σ(dimension.path_b_weight × score)` for all dimensions with non-zero path_b_weight (including dimensions that are not gates but contribute to ranking)

#### Scenario: Items ranked by weighted sum within included set
- **WHEN** multiple items pass the gates
- **THEN** items are sorted by `weighted_sum` descending before `max_posts` cap is applied

---

### Requirement: Run log written per profile execution
After scoring and filtering, the runner SHALL write a JSON file to `data/blog-runs/YYYY-MM-DD-{profile}.json` containing: `profile`, `run_at` (ISO-8601), `items_evaluated`, `items_included`, `items_excluded`, and a `results` array with full dimension scores, reasons, path results, weighted sum, and include/exclude decision for every evaluated item.

#### Scenario: Run log written on successful execution
- **WHEN** `horizon-blog` completes scoring for a profile
- **THEN** a JSON run log is written to `data/blog-runs/` regardless of how many items passed

#### Scenario: Run log written even when zero items pass
- **WHEN** no items pass the gates for a profile
- **THEN** the run log is still written with `items_included: 0` and all items in `results` with `included: false`

---

### Requirement: Console output displays scoring table per profile
The runner SHALL print a table to the console showing, for each evaluated item: its title, per-dimension scores, weighted sum, and include/exclude decision with the winning path or failed gate names.

#### Scenario: Scoring table printed after LLM call
- **WHEN** scoring completes for a profile
- **THEN** the console shows one row per item with dimension scores, weighted sum, and decision

#### Scenario: Failed gates named in console output
- **WHEN** an item is excluded
- **THEN** the console output identifies which dimension(s) caused the failure
