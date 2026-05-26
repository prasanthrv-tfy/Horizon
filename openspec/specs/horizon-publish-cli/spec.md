## ADDED Requirements

### Requirement: horizon-publish entry point
The system SHALL expose a `horizon-publish` CLI command registered in `pyproject.toml` pointing to `src/blog/publisher/runner.py::main`.

#### Scenario: Command is available after install
- **WHEN** `uv run horizon-publish` is executed
- **THEN** the command SHALL run without ImportError or entry-point error

### Requirement: horizon-publish reads generated blog posts
The `horizon-publish` CLI SHALL scan `artifacts/blog-posts/` for `posts.json` manifest files produced by `horizon-blog`, collecting all entries from `artifacts/blog-posts/*/posts.json` across profile subdirectories. For each entry, the CLI SHALL load the paired markdown file from the same directory as the manifest.

#### Scenario: Posts found
- **WHEN** `artifacts/blog-posts/` contains one or more `posts.json` manifest files with entries
- **THEN** the CLI SHALL log the count of posts found

#### Scenario: No posts found
- **WHEN** `artifacts/blog-posts/` contains no `posts.json` files, or all manifests are empty
- **THEN** the CLI SHALL print a warning and exit cleanly (exit code 0)

### Requirement: horizon-publish fetches existing Webflow items
The `horizon-publish` CLI SHALL call `WebflowPublisher.list_items(since)` using the configured `deduplication_time_window` to retrieve existing collection items before processing local posts.

#### Scenario: Items fetched successfully
- **WHEN** `horizon-publish` runs with a valid `WEBFLOW_TOKEN` and `collection_id`
- **THEN** it SHALL fetch Webflow items from the past `deduplication_time_window` days and print the count of items found

### Requirement: horizon-publish deduplicates and pushes drafts
The `horizon-publish` CLI SHALL deduplicate local posts against Webflow items, then for each kept post: load, convert to HTML, generate SEO fields, and call `add_draft`.

#### Scenario: Some posts filtered
- **WHEN** deduplication finds matching titles
- **THEN** the CLI SHALL skip duplicates and push only the non-matching posts as drafts

#### Scenario: No duplicates found
- **WHEN** no local post titles match any Webflow item
- **THEN** the CLI SHALL push all discovered posts as drafts

#### Scenario: All posts are duplicates
- **WHEN** all local posts match Webflow items
- **THEN** the CLI SHALL print a message indicating no new posts to publish and exit cleanly

### Requirement: horizon-publish pushes kept posts as drafts
For each kept post, `horizon-publish` SHALL load the post, convert Markdown to HTML, generate SEO fields via AI, call `WebflowPublisher.add_draft`, and log the result.

#### Scenario: Successful draft creation
- **WHEN** `add_draft` returns successfully
- **THEN** the CLI SHALL print a success line showing the post title and the Webflow item ID

#### Scenario: Failed draft creation
- **WHEN** `add_draft` raises a `RuntimeError`
- **THEN** the CLI SHALL log an error for that post and continue processing remaining posts

### Requirement: horizon-publish prints a run summary
After processing all posts, `horizon-publish` SHALL print a summary showing total pushed, total skipped (duplicates), and total failed.

#### Scenario: Summary after mixed run
- **WHEN** some posts are pushed, some skipped, and some failed
- **THEN** the CLI SHALL print counts for each category at the end of the run

### Requirement: horizon-publish validates collection_id before API calls
The `horizon-publish` CLI SHALL verify `blog.publisher.collection_id` is non-empty and exit with a clear error if it is missing, before attempting any Webflow API call.

#### Scenario: Missing collection_id
- **WHEN** `blog.publisher.collection_id` is empty or absent from config
- **THEN** the CLI SHALL print an error message and exit with a non-zero exit code

### Requirement: horizon-publish requires WEBFLOW_TOKEN
The `horizon-publish` CLI SHALL check that the `WEBFLOW_TOKEN` environment variable is set and exit with a clear error message if it is missing.

#### Scenario: Missing token
- **WHEN** `WEBFLOW_TOKEN` is not set in the environment
- **THEN** the CLI SHALL print an error and exit with a non-zero exit code

#### Scenario: Token present
- **WHEN** `WEBFLOW_TOKEN` is set
- **THEN** the CLI SHALL proceed to the next step without error
