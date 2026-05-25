## MODIFIED Requirements

### Requirement: horizon-blog command reads pipeline output and generates blog posts
The `horizon-blog` CLI command SHALL read `data/pipeline-output/important_items.json`, re-rank items by AI relevance **per profile using that profile's audience context**, and generate individual Markdown blog posts for each item in each configured language. Item selection (top-N) SHALL happen independently for each profile after its profile-specific ranking.

#### Scenario: Successful blog generation
- **WHEN** `uv run horizon-blog` is executed and `data/pipeline-output/important_items.json` exists with items
- **THEN** blog posts are written to `data/blog-posts/` and `docs/_posts/` for each item × language combination

#### Scenario: Missing input file
- **WHEN** `uv run horizon-blog` is executed and `data/pipeline-output/important_items.json` does not exist
- **THEN** the command exits with a clear error message indicating the file is missing and `horizon` must be run first

#### Scenario: Empty input file
- **WHEN** `data/pipeline-output/important_items.json` contains an empty array
- **THEN** the command exits early with a message indicating no items to process

#### Scenario: Different profiles select different items
- **WHEN** `horizon-blog` runs with multiple profiles (e.g., `prompt_profile: "all"`)
- **THEN** each profile's ranking may produce a different top-N item selection, and posts are generated for those profile-specific items
