## ADDED Requirements

### Requirement: horizon-publish entry point
The system SHALL expose a `horizon-publish` CLI command registered in `pyproject.toml` pointing to `src/blog/publisher/runner.py::main`.

#### Scenario: Command is available after install
- **WHEN** `uv run horizon-publish` is executed
- **THEN** the command SHALL run without ImportError or entry-point error

### Requirement: horizon-publish reads generated blog posts
The `horizon-publish` CLI SHALL scan `artifacts/blog-posts/` for Markdown files produced by `horizon-blog`, collecting all `*.md` files across profile subdirectories.

#### Scenario: Posts found
- **WHEN** `artifacts/blog-posts/` contains Markdown files
- **THEN** the CLI SHALL log the count and filenames of discovered posts

#### Scenario: No posts found
- **WHEN** `artifacts/blog-posts/` is empty or does not exist
- **THEN** the CLI SHALL print a warning and exit cleanly (exit code 0)

### Requirement: horizon-publish dry-run in Phase 1
In Phase 1, the `horizon-publish` CLI SHALL perform a dry-run only — logging which posts it would publish without making any Webflow API calls.

#### Scenario: Dry-run output
- **WHEN** `uv run horizon-publish` is executed with valid posts present
- **THEN** the CLI SHALL print each post title/filename it would publish, prefixed with a dry-run notice

### Requirement: horizon-publish requires WEBFLOW_TOKEN
The `horizon-publish` CLI SHALL check that the `WEBFLOW_TOKEN` environment variable is set and exit with a clear error message if it is missing.

#### Scenario: Missing token
- **WHEN** `WEBFLOW_TOKEN` is not set in the environment
- **THEN** the CLI SHALL print an error and exit with a non-zero exit code

#### Scenario: Token present
- **WHEN** `WEBFLOW_TOKEN` is set
- **THEN** the CLI SHALL proceed to the next step without error
