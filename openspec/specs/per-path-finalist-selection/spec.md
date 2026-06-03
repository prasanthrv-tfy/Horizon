# Per-path Finalist Selection Spec

## Requirements

### Requirement: Per-path finalist pool selection
The blog generator SHALL build a finalist pool by taking the top `max_posts` items (by `weighted_sum`) from each gate path independently, then uniformly randomly sampling `max_posts` items from the combined pool to form the final selection.

#### Scenario: Equal path representation when both paths have sufficient items
- **WHEN** multiple gate paths each have at least `max_posts` passing items
- **THEN** the finalist pool contains exactly `max_posts` items from each path, and `max_posts` items are randomly drawn from the pool

#### Scenario: Path with fewer items than max_posts contributes all its items
- **WHEN** a gate path has fewer passing items than `max_posts`
- **THEN** all items from that path enter the finalist pool (no padding or exclusion)

#### Scenario: Single active path falls back to score-based top-N
- **WHEN** only one gate path has any passing items
- **THEN** the top `max_posts` items from that path are selected by `weighted_sum` (no random draw; behaviour matches pre-change)

#### Scenario: --all-posts flag bypasses finalist selection
- **WHEN** the `--all-posts` CLI flag is set
- **THEN** all gate-passing items are used for blog generation regardless of path or pool logic

#### Scenario: --items flag bypasses finalist selection
- **WHEN** the `--items` CLI flag specifies explicit row numbers
- **THEN** only those items are used for blog generation, bypassing all gate and pool logic

#### Scenario: Selection is non-deterministic across runs
- **WHEN** the same `important_items.json` is processed on two successive runs with the same `max_posts`
- **THEN** the selected items MAY differ between runs due to uniform random sampling
