## ADDED Requirements

### Requirement: Draft vs live publish CLI toggle
The `horizon-publish` command SHALL accept a `--publish` flag. When absent, posts are pushed as Webflow drafts (`isDraft: true`). When present, posts are published live immediately (`isDraft: false`).

#### Scenario: Default run (no flag) creates drafts
- **WHEN** `uv run horizon-publish` is run without `--publish`
- **THEN** all pushed Webflow CMS items have `isDraft: true`

#### Scenario: `--publish` flag publishes live
- **WHEN** `uv run horizon-publish --publish` is run
- **THEN** all pushed Webflow CMS items have `isDraft: false` and are immediately visible on the site

### Requirement: `--generate-image` CLI flag
The `horizon-publish` command SHALL accept a `--generate-image` flag that activates AI cover image generation for the current run, overriding the `image_generation.enabled` config value.

#### Scenario: Flag enables image generation when config is disabled
- **WHEN** `--generate-image` is passed and `image_generation.enabled` is `false` in config
- **THEN** image generation runs for the current publish run

#### Scenario: Flag is additive with `--publish`
- **WHEN** both `--generate-image` and `--publish` are passed
- **THEN** posts are published live with AI cover images attached
