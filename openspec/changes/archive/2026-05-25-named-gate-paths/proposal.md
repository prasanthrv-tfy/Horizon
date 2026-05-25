## Why

Gate paths are currently opaque A/B/C labels auto-assigned from list position, and each `ScoringDimension` carries `path_a_weight`, `path_b_weight`, `path_c_weight`, and `path_thresholds` — meaning you must visit every dimension to understand a single path. Run data also confirms Path A is fully redundant (all Path A items pass B and C independently), adding complexity with no editorial value.

## What Changes

- **BREAKING** Introduce `GatePath` and `PathDimensionConfig` dataclasses: a path now owns its name, the dimensions it gates on, each dimension's threshold, and each dimension's weight
- **BREAKING** Remove `path_a_weight`, `path_b_weight`, `path_c_weight`, `path_thresholds` fields from `ScoringDimension` — dimensions are slimmed to `name`, `description`, `anchors` only
- Drop Path A from the practitioner profile (confirmed redundant from production run data)
- Rename Path B → `production_ready`, Path C → `research_significance`
- Update `runner.py` to compute gating and weighted sums from the new `GatePath` structure
- Update `ScoredItem.inclusion_path` to store the path name string (e.g. `"production_ready"`) instead of `"A"` / `"B"`
- Update ranking table output and run log JSON to use path names
- Update `docs/blog-profiles.md` to reflect the new structure

## Capabilities

### New Capabilities
- `named-gate-paths`: First-class `GatePath` objects with descriptive names, owning dimension weights and thresholds per path

### Modified Capabilities
- `multi-dimensional-scoring`: `ScoringDimension` schema changes (fields removed); `GatePath` replaces the plain `List[List[str]]` gate_paths structure
- `blog-prompt-profiles`: Practitioner profile drops Path A, renames B/C; profile definition format changes to use `GatePath` objects
- `profile-aware-ranking`: Output (ranking table, run log JSON, `inclusion_path`) uses path names instead of single letters

## Impact

- `src/blog/models.py` — new `GatePath`, `PathDimensionConfig` dataclasses; `ScoringDimension` fields removed
- `src/blog/runner.py` — gating and weighted sum logic rewritten against `GatePath`
- `src/blog/profiles/practitioner.py` — profile restructured with named paths
- `src/blog/profiles/journalist.py` — inspect and update if it uses `gate_paths`
- `artifacts/ranking_results.md` — auto-generated; format will change on next run
- `docs/blog-profiles.md` — documentation updated
- Run log JSON schema: `inclusion_path` values change from `"A"`/`"B"` to names
