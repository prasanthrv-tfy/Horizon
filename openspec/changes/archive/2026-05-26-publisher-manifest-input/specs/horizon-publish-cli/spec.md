## MODIFIED Requirements

### Requirement: horizon-publish reads generated blog posts
The `horizon-publish` CLI SHALL scan `artifacts/blog-posts/` for `posts.json` manifest files produced by `horizon-blog`, collecting all entries from `artifacts/blog-posts/*/posts.json` across profile subdirectories. For each entry, the CLI SHALL load the paired markdown file from the same directory as the manifest.

#### Scenario: Posts found
- **WHEN** `artifacts/blog-posts/` contains one or more `posts.json` manifest files with entries
- **THEN** the CLI SHALL log the count of posts found

#### Scenario: No posts found
- **WHEN** `artifacts/blog-posts/` contains no `posts.json` files, or all manifests are empty
- **THEN** the CLI SHALL print a warning and exit cleanly (exit code 0)
