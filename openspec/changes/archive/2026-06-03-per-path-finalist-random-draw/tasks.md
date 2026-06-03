## 1. Replace selection logic in runner.py

- [x] 1.1 In `src/blog/generator/runner.py`, replace the `included` sort-and-slice block (the lines that sort all passing items by `weighted_sum` and slice to `max_posts`) with the per-path finalist pool + random draw logic
- [x] 1.2 Import `random` at the top of `runner.py` (if not already present)
- [x] 1.3 Implement the single-path fallback: when only one path has passing items, use the original top-N sort (no random draw)

## 2. Verify edge cases

- [x] 2.1 Confirm `--all-posts` flag still bypasses the new logic (check that `max_posts is None` path is untouched)
- [x] 2.2 Confirm `--items` flag still bypasses gate and pool logic (check the explicit-items path in `runner.py`)
- [x] 2.3 Confirm behaviour when a path has fewer items than `max_posts` (all items from that path enter the pool)

## 3. Manual verification

- [x] 3.1 Run `uv run horizon-blog --profile engineer --max-posts 4` and verify the output includes items from both `engineering_applicability` and `technical_insights` paths (check the console path breakdown table)
- [x] 3.2 Run the same command a second time and confirm the selected items differ (demonstrating non-determinism)
- [x] 3.3 Inspect `artifacts/blog-runs/` log to confirm `inclusion_path` is recorded for each selected item
