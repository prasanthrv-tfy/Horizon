## MODIFIED Requirements

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
