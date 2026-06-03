## Why

When multiple gate paths compete for the same output slots, sorting all passing items by a single `weighted_sum` causes whichever path produces more high-scoring items (Path A, with lower thresholds) to dominate entirely — Path B items never surface even when they are the best of their kind. Since the paths represent different but equally valid editorial intents (production-ready vs. deep-insight content), the selection mechanism should give each path equal representation opportunity.

## What Changes

- Replace the current single-list sort-and-slice with a per-path finalist pool + uniform random draw.
- For each gate path, take the top `max_posts` items (by `weighted_sum`) as finalists.
- Pool all finalists across paths, then uniformly randomly sample `max_posts` items for the final selection.
- If a path produces fewer than `max_posts` passing items, all of them enter the pool.
- If only one path has passing items, behaviour is unchanged (top-N from that path).
- `--items` and `--all-posts` CLI flags bypass the new logic entirely (no change).

## Capabilities

### New Capabilities
- `per-path-finalist-selection`: Blog post selection strategy that takes top-N finalists from each gate path independently, pools them, and randomly draws the final set — ensuring all paths get representation opportunity regardless of raw score distribution.

### Modified Capabilities

## Impact

- `src/blog/generator/runner.py` — the `included` sort-and-slice block (lines 156–168) is replaced with the new selection logic.
- No model changes (`GatePath`, `ScoredItem`, `ScoringDimension` are unchanged).
- No config changes — pool size per path is implicitly `max_posts`.
- Run logs in `artifacts/blog-runs/` should record which path each selected item came from (already tracked via `ScoredItem.inclusion_path`).
- Daily scheduled runs benefit from randomness: high-scoring items that miss one draw will resurface in subsequent runs.
