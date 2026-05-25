## MODIFIED Requirements

### Requirement: horizon-blog command reads pipeline output and generates blog posts
The `horizon-blog` CLI command SHALL read `data/pipeline-output/important_items.json`, score items per profile using multi-dimensional scoring when `scoring_dimensions` are defined, apply gate filtering, rank included items by weighted sum, and generate individual Markdown blog posts for each included item in each configured language. Zero posts is a valid outcome when no items pass the gates.

#### Scenario: Successful blog generation with gate filtering
- **WHEN** `uv run horizon-blog` is executed and items pass the profile's gate thresholds
- **THEN** blog posts are written to `data/blog-posts/` and `docs/_posts/` only for items that passed the gates

#### Scenario: Missing input file
- **WHEN** `uv run horizon-blog` is executed and `data/pipeline-output/important_items.json` does not exist
- **THEN** the command exits with a clear error message indicating the file is missing and `horizon` must be run first

#### Scenario: Empty input file
- **WHEN** `data/pipeline-output/important_items.json` contains an empty array
- **THEN** the command exits early with a message indicating no items to process

#### Scenario: No items pass the gates
- **WHEN** all items fail the profile's gate thresholds
- **THEN** no blog posts are generated, the run log is still written, and the console prints a clear message indicating zero items passed

#### Scenario: Different profiles select different items
- **WHEN** `horizon-blog` runs with multiple profiles (e.g., `prompt_profile: "all"`)
- **THEN** each profile's gate logic independently determines which items are included, and posts are generated for those profile-specific items
