## ADDED Requirements

### Requirement: Generator writes posts.json manifest per profile run
After generating all blog posts for a profile, the generator SHALL write a single `artifacts/blog-posts/{profile}/posts.json` file containing a JSON array of metadata objects — one per generated post across all languages.

Each entry SHALL contain: `item_id`, `title`, `slug`, `score`, `tags`, `url`, `published_at`, `language`, `profile`, `filename`.

The `score` field SHALL be the blog generator's own score: `ScoredItem.weighted_sum` for profiles with `scoring_dimensions` (gate profiles), and `ContentItem.ai_score` for legacy profiles without dimensions.

The `filename` field SHALL be the basename of the paired markdown file (e.g. `2026-05-25-my-slug-en.md`).

#### Scenario: Gate profile run produces manifest with weighted_sum scores
- **WHEN** `horizon-blog` runs with a profile that has `scoring_dimensions` (e.g. `engineer`)
- **THEN** `artifacts/blog-posts/engineer/posts.json` SHALL exist and each entry's `score` SHALL equal the `ScoredItem.weighted_sum` for that item

#### Scenario: Legacy profile run produces manifest with ai_score
- **WHEN** `horizon-blog` runs with a profile that has no `scoring_dimensions` (e.g. `news`)
- **THEN** `artifacts/blog-posts/news/posts.json` SHALL exist and each entry's `score` SHALL equal `ContentItem.ai_score`

#### Scenario: Multi-language run includes one entry per post per language
- **WHEN** `horizon-blog` generates posts in multiple languages
- **THEN** `posts.json` SHALL contain one entry per (post × language) combination, each with the correct `language` field

#### Scenario: Re-running replaces the manifest
- **WHEN** `horizon-blog` is run a second time for the same profile
- **THEN** `posts.json` SHALL be overwritten with only the posts from the latest run

### Requirement: Generator stops writing to docs/_posts/
The generator SHALL NOT write Jekyll front-matter files to `docs/_posts/` as part of `horizon-blog` execution.

#### Scenario: docs/_posts/ not written
- **WHEN** `horizon-blog` runs successfully
- **THEN** no new files SHALL appear under `docs/_posts/`
