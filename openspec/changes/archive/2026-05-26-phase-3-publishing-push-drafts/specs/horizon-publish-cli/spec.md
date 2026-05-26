## MODIFIED Requirements

### Requirement: horizon-publish deduplicates before listing candidates
The `horizon-publish` CLI SHALL pass discovered local posts and fetched Webflow items through `deduplicate_posts()`, then push each kept post as a draft rather than just listing candidates.

#### Scenario: Some posts filtered
- **WHEN** deduplication finds matching titles between local posts and Webflow items
- **THEN** the CLI SHALL skip duplicates (log "already in Webflow") and push only the non-matching posts

#### Scenario: No duplicates found
- **WHEN** no local post titles match any Webflow item
- **THEN** the CLI SHALL push all discovered posts as drafts

#### Scenario: All posts are duplicates
- **WHEN** all local posts match Webflow items
- **THEN** the CLI SHALL print a message indicating no new posts to publish and exit cleanly

## ADDED Requirements

### Requirement: horizon-publish pushes kept posts as drafts
For each kept post, `horizon-publish` SHALL: load the post from disk, convert Markdown to HTML, generate SEO fields via AI, call `WebflowPublisher.add_draft`, and log the result.

#### Scenario: Successful draft creation
- **WHEN** a kept post is processed and `add_draft` returns successfully
- **THEN** the CLI SHALL print a success line showing the post title and the Webflow item ID

#### Scenario: Failed draft creation
- **WHEN** `add_draft` raises a `RuntimeError` for a post
- **THEN** the CLI SHALL log an error for that post and continue processing remaining posts

### Requirement: horizon-publish prints a run summary
After processing all posts, `horizon-publish` SHALL print a summary showing total pushed, total skipped (duplicates), and total failed.

#### Scenario: Summary after mixed run
- **WHEN** some posts are pushed, some skipped, and some failed
- **THEN** the CLI SHALL print counts for each category at the end of the run
