# Named Gate Paths Spec

## Requirements

### Requirement: GatePath is a named first-class object owning its dimension configs
A `GatePath` dataclass SHALL exist in `src/blog/models.py` with fields `name: str` and `dimensions: List[PathDimensionConfig]`. Each `PathDimensionConfig` SHALL have `dimension: str` (matching a `ScoringDimension.name` in the profile), `weight: float`, and `threshold: float`.

#### Scenario: GatePath instantiated with name and dimensions
- **WHEN** a `GatePath` is created with a name and a list of `PathDimensionConfig` entries
- **THEN** all fields are accessible and the path can be used in `BlogPromptProfile.gate_paths`

#### Scenario: PathDimensionConfig carries threshold and weight
- **WHEN** a `PathDimensionConfig` is created with dimension, weight, and threshold
- **THEN** `threshold` is used as the gate bar for that dimension in that path, and `weight` is used in the weighted sum

### Requirement: Gate evaluation and weighted sum are driven entirely from GatePath
The runner SHALL evaluate gates by iterating `gate_path.dimensions` and comparing each dimension's score against `PathDimensionConfig.threshold`. Weighted sum SHALL be computed as `Σ(pdc.weight × score)` over the winning path's `dimensions`.

#### Scenario: Item passes a named gate path
- **WHEN** all dimensions in a `GatePath` score at or above their `PathDimensionConfig.threshold`
- **THEN** the item is included and `ScoredItem.inclusion_path` is set to `gate_path.name`

#### Scenario: Weighted sum uses path-specific weights
- **WHEN** an item is included via `GatePath(name="production_ready", ...)`
- **THEN** `weighted_sum = Σ(pdc.weight × score)` for that path's `PathDimensionConfig` entries

#### Scenario: Excluded item gets best-possible sum for logging
- **WHEN** an item fails all gate paths
- **THEN** `weighted_sum` is the maximum `_compute_weighted_sum` across all paths, for reference in the ranking table

### Requirement: ScoringDimension is path-agnostic
`ScoringDimension` SHALL contain only `name: str`, `description: str`, and `anchors: Dict[str, str]`. It SHALL NOT contain any weight or threshold fields. All weight and threshold information SHALL live in `PathDimensionConfig`.

#### Scenario: ScoringDimension has no weight or threshold fields
- **WHEN** a `ScoringDimension` is instantiated
- **THEN** it exposes only `name`, `description`, and `anchors` — accessing `gate_threshold`, `path_a_weight`, or similar raises `AttributeError`

### Requirement: inclusion_path stores the gate path name string
`ScoredItem.inclusion_path` SHALL store the `GatePath.name` string (e.g. `"production_ready"`) for included items, or `None` for excluded items. Single-letter labels (`"A"`, `"B"`, `"C"`) SHALL NOT be used.

#### Scenario: Included item has named inclusion_path
- **WHEN** an item passes the `production_ready` gate path
- **THEN** `ScoredItem.inclusion_path == "production_ready"`

#### Scenario: Excluded item has None inclusion_path
- **WHEN** an item fails all gate paths
- **THEN** `ScoredItem.inclusion_path is None`
