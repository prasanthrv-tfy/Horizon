# Profile-Aware Ranking Spec

## Requirements

### Requirement: BlogPromptProfile carries a ranking_context field
**DEPRECATED** — superseded by `scoring_dimensions` and `gate_paths` on `BlogPromptProfile`. The `ranking_context` string is insufficient to drive gate-based filtering with per-dimension thresholds. The field is retained for backwards compatibility but is ignored when `scoring_dimensions` is non-empty.

---

### Requirement: rank_by_relevance accepts optional audience context
**DEPRECATED** — `rank_by_relevance()` is replaced by `score_items_for_profile()` for profiles with scoring dimensions. The audience context concept is now expressed through `ScoringDimension` definitions and their anchors. `rank_by_relevance()` remains available as a fallback for profiles without scoring dimensions.

---

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
