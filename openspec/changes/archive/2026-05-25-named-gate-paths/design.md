## Context

The blog scoring system evaluates content items across named dimensions (e.g. `ml_engineering_relevance`, `technical_substance`) and routes items through gate paths — a series of AND-gated thresholds that determine inclusion. Currently:

- Paths are anonymous: auto-labeled A/B/C from list position in `gate_paths: List[List[str]]`
- Each `ScoringDimension` carries `path_a_weight`, `path_b_weight`, `path_c_weight`, and `path_thresholds` — the dimension owns the relationship to each path
- To understand what Path B does, you must scan every dimension and extract its `path_b_weight`
- Production run data confirms Path A is fully redundant: every item that passes Path A also independently passes Path B and Path C — it never does unique editorial work

The journalist profile has one path; the practitioner profile has three. The weight-on-dimension design scales badly as profiles and paths grow.

## Goals / Non-Goals

**Goals:**
- Make each gate path a named, self-contained object that declares which dimensions it gates on, at what threshold, and with what weight
- Slim `ScoringDimension` to purely describe the scoring axis: `name`, `description`, `anchors`
- Drop the redundant Path A from the practitioner profile
- Rename practitioner paths to `production_ready` and `research_significance`
- Propagate path names through all output: `inclusion_path`, ranking table, run log JSON

**Non-Goals:**
- Changing scoring logic or LLM prompts
- Adding OR-logic within a path (stays AND-gated)
- Changing how dimensions are scored (one LLM call per item across all dimensions)
- Migrating old run log JSON files

## Decisions

### 1. New dataclasses: `PathDimensionConfig` and `GatePath`

```python
@dataclass
class PathDimensionConfig:
    dimension: str   # must match a ScoringDimension.name in the profile
    weight: float
    threshold: float  # gate threshold for this dimension in this path

@dataclass
class GatePath:
    name: str                              # e.g. "production_ready"
    dimensions: List[PathDimensionConfig]  # ordered list; all must pass (AND logic)
```

`BlogPromptProfile.gate_paths` changes type from `List[List[str]]` to `List[GatePath]`.

**Alternative considered:** keep `gate_paths` as `List[List[str]]` and add a separate `path_configs` dict. Rejected — splits the definition across two structures and requires cross-referencing.

### 2. `ScoringDimension` loses all path knowledge

Remove: `path_a_weight`, `path_b_weight`, `path_c_weight`, `path_thresholds`, `gate_threshold`.

`gate_threshold` is removed entirely — each `PathDimensionConfig` specifies its own threshold explicitly. There is no fallback default. Every path must declare every threshold for its dimensions. This is more verbose but eliminates the hidden layering between `gate_threshold` and `path_thresholds`.

**Alternative considered:** keep `gate_threshold` as a default that `PathDimensionConfig.threshold` overrides. Rejected — the "default plus override" pattern is exactly the obscurity we're removing.

### 3. Runner rewrite: gating and weighted sum driven from `GatePath`

`_compute_weighted_sum` currently switches on path label string ("A"/"B"/"C") to pick the right weight field. Replace with:

```python
def _compute_weighted_sum(dim_scores: dict, gate_path: GatePath) -> float:
    total = 0.0
    for pdc in gate_path.dimensions:
        score = dim_scores.get(pdc.dimension, {}).get("score", 0)
        total += pdc.weight * score
    return round(total, 3)
```

Gate evaluation loop replaces `chr(ord("A") + path_idx)` label generation with `gate_path.name`.

For excluded items, the "best possible sum" is computed by calling `_compute_weighted_sum` over each `GatePath` and taking the max — same logic, just using the new structure.

**Note:** Dimensions that appear in the profile's `scoring_dimensions` but in no `GatePath` are still scored by the LLM (for observability), but contribute 0 weight to any path. This matches current behaviour for dimensions with all-zero weights.

### 4. `ScoredItem.inclusion_path` stores path name, not letter

`inclusion_path: Optional[str]` already exists — value changes from `"A"` / `"B"` to `"production_ready"` / `"research_significance"`. No type change needed.

`path_results` dict key changes from `"A"` / `"B"` to path names. Run log JSON `path_results` keys change accordingly.

### 5. Journalist profile: single named path

The journalist profile's single-path `gate_paths` list becomes:

```python
gate_paths=[
    GatePath(
        name="editorial",
        dimensions=[
            PathDimensionConfig("significance",      weight=0.45, threshold=6.0),
            PathDimensionConfig("newsworthiness",    weight=0.35, threshold=5.0),
            PathDimensionConfig("narrative_clarity", weight=0.20, threshold=4.0),
        ]
    )
]
```

## Risks / Trade-offs

- **Existing run log JSON breaks** → `path_results` keys and `inclusion_path` values change. Old logs remain readable but keys differ. No migration needed — logs are append-only historical artifacts.
- **Profile definition is more verbose** → Each path must list all its dimensions explicitly with thresholds. This is intentional: verbosity in the profile file buys clarity; the old design's compactness hid information across dimension definitions.
- **Dimensions not in any GatePath** → Still scored, still visible in output, weight is implicitly 0. This is fine and matches current `path_x_weight=0.0` behaviour. No special handling needed.

## Migration Plan

1. Update `src/blog/models.py` — add `PathDimensionConfig`, `GatePath`; slim `ScoringDimension`
2. Update `src/blog/runner.py` — rewrite `_compute_weighted_sum` and gate evaluation loop
3. Update `src/blog/profiles/practitioner.py` — drop Path A, define two named `GatePath` objects
4. Update `src/blog/profiles/journalist.py` — wrap single path in a named `GatePath`
5. Update `src/blog/profiles/profile.py` — change `gate_paths` type annotation
6. Update `docs/blog-profiles.md` — reflect new structure and path names
7. Verify: run `uv run horizon-blog --rank-only` and confirm path names appear in output

No database migrations, no dependency changes, no API surface changes.
