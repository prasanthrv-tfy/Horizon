## Context

The blog generator scores items across multiple gate paths. Each item passes the first path whose thresholds it meets and receives a `weighted_sum` from that path's weight formula. Currently, all passing items are sorted by `weighted_sum` in a single combined list and sliced to `max_posts`.

Because Path A ("engineering_applicability") has lower thresholds (ml_eng ≥ 7, prod_ap ≥ 7) than Path B ("technical_insights") (ml_eng ≥ 8, engi ≥ 6), Path A admits more items and those items score higher in absolute terms. In the 2026-06-01 run: Path A produced 30 passing items (top score 8.80), Path B produced 18 (top score 7.70). With `max_posts=4`, all 4 selected posts came from Path A.

The fix lives entirely in `runner.py` at the post-scoring selection step.

## Goals / Non-Goals

**Goals:**
- Ensure all gate paths have equal representation opportunity in the final selection.
- Keep the change isolated to `runner.py`; no model, profile, or config changes.
- Preserve all existing CLI flags (`--items`, `--all-posts`, `--rank-only`).
- Keep the run log traceable — selected items already carry `inclusion_path`.

**Non-Goals:**
- Weighting paths differently (e.g., 2 slots guaranteed for Path B).
- Making pool size configurable per path.
- Changing how items are scored or which path they are assigned to.

## Decisions

### D1: Pool size per path = `max_posts`

**Decision**: Each gate path contributes its top `max_posts` items to the finalist pool (or all items if fewer than `max_posts` pass).

**Rationale**: This gives every path equal "voting power" regardless of how many items it admits. Using a fixed multiplier (e.g., 2×) would require more config surface and is harder to reason about. Using `max_posts` is intuitive: "each path nominates as many finalists as the total output."

**Alternative considered**: A configurable `finalists_per_path` on `GatePath`. Rejected — adds config complexity without meaningful benefit given the use case.

### D2: Uniform random draw (not score-weighted)

**Decision**: Sample `max_posts` items from the pool using `random.sample` (uniform, without replacement).

**Rationale**: The run is scheduled daily. High-scoring items that miss one draw will resurface in subsequent runs. Uniform sampling maximises diversity over time and avoids the complexity of maintaining and calibrating score weights across paths with different score distributions.

**Alternative considered**: `random.choices` with `weighted=weighted_sum`. Rejected — score distributions differ between paths (Path B items cluster tightly 6.55–7.70 vs Path A's 6.55–8.80), so raw `weighted_sum` as a weight would reintroduce the same Path A bias at lower intensity.

### D3: Single-path fallback = current behaviour

**Decision**: If only one path has any passing items, use the existing sort-and-slice logic (top-N by `weighted_sum`).

**Rationale**: Ensures no regression when the pipeline is run on a small item set or a profile with only one gate path (e.g., the `news` profile).

## Risks / Trade-offs

- **[Non-determinism]** → Same data can produce different posts across runs. Mitigated by daily scheduling — diversity is the intended property. Run logs record which items were drawn and from which path.
- **[Path B item quality floor]** → Finalists include Path B's top-4, which may have lower absolute scores than Path A's top-8. Mitigated by the fact that Path B has a harder ml_eng gate (≥ 8), so its finalists are still high-relevance items.
- **[Tie-breaking in top-N per path]** → When items have equal `weighted_sum`, `sort` order is stable (Python sort preserves insertion order). No randomness is introduced at the finalist selection step — only at the final draw.
