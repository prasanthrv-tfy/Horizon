## Why

The practitioner profile's gate structure has two problems discovered through real runs: Path A (technical depth) is letting in business partnership announcements because `technical_substance >= 5` is too loose, and Path B (ecosystem event) is letting in secondary journalism (Wired roundups of Google I/O) because `ai_ecosystem_significance` scoring is inflated for derivative coverage. More fundamentally, `production_applicability` as a gate on every path incorrectly excludes valuable research papers that aren't immediately deployable but are exactly what ML engineers need to stay current.

## What Changes

- **Redefine `technical_substance`** to explicitly include deployable models and working APIs as concrete technical artifacts alongside papers and repos. Revised anchors make the 7+ range require a real artifact (model accessible via API, paper with details) and push partnership announcements without artifacts to 2-3.
- **Redesign Path A** (Research awareness): `ml_engineering_relevance >= 7` AND `technical_substance >= 7`. No `production_applicability` gate. Higher bar on both dimensions ensures only genuinely deep research passes. Captures papers, new techniques, evaluation approaches, scaling findings.
- **Redesign Path B** (Production ready): `ml_engineering_relevance >= 6` AND `technical_substance >= 6` AND `production_applicability >= 6`. The revised `technical_substance` definition means model releases and new APIs naturally pass this path.
- **Remove `ai_ecosystem_significance` from `gate_paths`**. It stays as a `scoring_dimension` and contributes to the weighted sum for ranking, but is no longer a gate. Model releases from key providers pass Path B on their own merits without needing a separate path that inflates scores for secondary coverage.
- Raise `ml_engineering_relevance` gate for Path A from 6 to 7.

## Capabilities

### New Capabilities

*(none — this is a configuration change to an existing profile)*

### Modified Capabilities

- `multi-dimensional-scoring`: The practitioner profile's `scoring_dimensions` and `gate_paths` change. `ScoringDimension` for `technical_substance` gets a new description and anchors. `gate_paths` changes from `[["ml_engineering_relevance", "technical_substance", "production_applicability"], ["ai_ecosystem_significance", "production_applicability"]]` to `[["ml_engineering_relevance", "technical_substance"], ["ml_engineering_relevance", "technical_substance", "production_applicability"]]`. `ai_ecosystem_significance` is removed from gate paths.

## Impact

- `src/blog/profiles/practitioner.py` only — dimension definitions, anchors, thresholds, and gate_paths.
- No changes to `src/blog/runner.py`, `src/blog/models.py`, `src/blog/prompts.py`, or any other file.
