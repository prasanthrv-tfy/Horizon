## MODIFIED Requirements

### Requirement: Ranking runs independently per profile
The blog runner SHALL call scoring or ranking once per profile (inside the profile loop). When a profile has `scoring_dimensions` defined, `score_items_for_profile()` is used and gate filtering is applied. When `scoring_dimensions` is empty, `rank_by_relevance()` is used as a fallback and top-N selection applies without gate filtering.

#### Scenario: Profile with scoring_dimensions uses scoring path
- **WHEN** `horizon-blog` runs with a profile that has non-empty `scoring_dimensions`
- **THEN** `score_items_for_profile()` is called, gate filtering is applied, and items are ranked by weighted sum

#### Scenario: Profile without scoring_dimensions uses ranking fallback
- **WHEN** `horizon-blog` runs with a profile that has empty `scoring_dimensions`
- **THEN** `rank_by_relevance()` is called and top-N selection is applied without gate filtering

#### Scenario: Two profiles produce different selections
- **WHEN** `horizon-blog` runs with `prompt_profile: "all"` and profiles have different `scoring_dimensions`
- **THEN** each profile's scoring independently determines which items are included

#### Scenario: Selected items logged per profile
- **WHEN** scoring or ranking completes for a profile
- **THEN** the console output identifies which items were selected (or excluded) for that profile

---

### Requirement: Ranking output uses gate path names instead of single letters
The ranking table (console output, `artifacts/ranking_results.md`), run log JSON, and `ScoredItem.inclusion_path` SHALL use the `GatePath.name` string (e.g. `"production_ready"`) to identify which path an item passed. Single-letter labels (`"A"`, `"B"`, `"C"`) SHALL NOT appear in any output.

#### Scenario: Ranking table shows path name for included item
- **WHEN** an item passes the `production_ready` gate path
- **THEN** the ranking table and run log JSON show `"production_ready"` as the decision/path, not `"B"`

#### Scenario: Run log JSON inclusion_path uses path name
- **WHEN** the run log is written to `artifacts/blog-runs/`
- **THEN** each result entry's `inclusion_path` field is a gate path name string or `null`, never a single letter
