## MODIFIED Requirements

### Requirement: BlogPromptProfile carries gate_paths as List[GatePath]
`BlogPromptProfile` SHALL have `gate_paths: List[GatePath]` (default empty list). Each entry is a `GatePath` with a descriptive `name` and a list of `PathDimensionConfig` entries. The field SHALL NOT be `List[List[str]]`.

#### Scenario: BlogPromptProfile gate_paths contains named GatePath objects
- **WHEN** a `BlogPromptProfile` is instantiated with `gate_paths`
- **THEN** each entry is a `GatePath` with a non-empty `name` and at least one `PathDimensionConfig`

---

### Requirement: Practitioner profile defines two named gate paths
The practitioner profile SHALL define exactly two `GatePath` objects: `production_ready` and `research_significance`. Path A (the former unnamed first path) SHALL be removed. The profile SHALL NOT define any path labeled "A", "B", or "C".

#### Scenario: Practitioner profile has production_ready path
- **WHEN** the practitioner profile is loaded
- **THEN** `gate_paths` contains a `GatePath` with `name == "production_ready"` gating on `ml_engineering_relevance`, `technical_substance`, `production_applicability`, and `ai_ecosystem_significance`

#### Scenario: Practitioner profile has research_significance path
- **WHEN** the practitioner profile is loaded
- **THEN** `gate_paths` contains a `GatePath` with `name == "research_significance"` gating on `ml_engineering_relevance`, `technical_substance`, and `engineering_insight`

#### Scenario: Practitioner profile has no Path A
- **WHEN** the practitioner profile is loaded
- **THEN** `len(gate_paths) == 2` and no path with only `ml_engineering_relevance` + `technical_substance` (and no other dimensions) exists

---

### Requirement: Journalist profile defines one named gate path
The journalist profile SHALL define exactly one `GatePath` with `name == "editorial"`, gating on `significance`, `newsworthiness`, and `narrative_clarity` with the same thresholds and weights as the former unnamed single path.

#### Scenario: Journalist profile has editorial path
- **WHEN** the journalist profile is loaded
- **THEN** `gate_paths` contains exactly one `GatePath` with `name == "editorial"`
