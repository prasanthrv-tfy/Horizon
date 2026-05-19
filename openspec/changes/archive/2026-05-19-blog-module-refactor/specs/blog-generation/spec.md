## ADDED Requirements

### Requirement: Pipeline saves important items to file
After threshold filtering and topic deduplication, the `horizon` pipeline SHALL serialize the `important_items` list to `data/pipeline-output/important_items.json` as a JSON array of `ContentItem` objects.

#### Scenario: Items saved after filtering
- **WHEN** the `horizon` pipeline completes threshold filtering and topic dedup
- **THEN** `data/pipeline-output/important_items.json` is written with all items above the score threshold

#### Scenario: Empty result writes empty array
- **WHEN** no items pass the score threshold
- **THEN** `data/pipeline-output/important_items.json` is written with an empty JSON array `[]`

---

### Requirement: horizon-blog command reads pipeline output and generates blog posts
The `horizon-blog` CLI command SHALL read `data/pipeline-output/important_items.json`, optionally re-rank items by AI relevance, and generate individual Markdown blog posts for each item in each configured language.

#### Scenario: Successful blog generation
- **WHEN** `uv run horizon-blog` is executed and `data/pipeline-output/important_items.json` exists with items
- **THEN** blog posts are written to `data/blog-posts/` and `docs/_posts/` for each item × language combination

#### Scenario: Missing input file
- **WHEN** `uv run horizon-blog` is executed and `data/pipeline-output/important_items.json` does not exist
- **THEN** the command exits with a clear error message indicating the file is missing and `horizon` must be run first

#### Scenario: Empty input file
- **WHEN** `data/pipeline-output/important_items.json` contains an empty array
- **THEN** the command exits early with a message indicating no items to process

---

### Requirement: Blog output format is preserved
The `horizon-blog` command SHALL produce blog posts in the same format as the previous inline implementation — raw Markdown in `data/blog-posts/` and Jekyll-ready files with front matter in `docs/_posts/`.

#### Scenario: Jekyll front matter is written
- **WHEN** a blog post is generated
- **THEN** the file in `docs/_posts/` contains a YAML front matter block with `layout`, `type`, `title`, `date`, `lang`, `score`, `original_url`, and `tags` fields

#### Scenario: Leading H1 stripped for Jekyll
- **WHEN** the generated Markdown starts with a `# ` heading
- **THEN** the Jekyll file omits that heading (to avoid duplication with the Jekyll title)

---

### Requirement: BlogConfig controls blog generation behaviour
The `blog` section of `config.json` (optional) SHALL control blog generation parameters including maximum number of posts and relevance ranking topics.

#### Scenario: Default config used when blog section absent
- **WHEN** `data/config.json` has no `blog` section
- **THEN** `horizon-blog` runs with default values: `max_posts=4`, `topics=[]`

#### Scenario: max_posts limits output
- **WHEN** `blog.max_posts` is set to N and more than N items are in the input file
- **THEN** only the top N items (by relevance ranking) are used for blog generation

---

### Requirement: Relevance ranking is performed within the blog module
The `src/blog/runner.py` module SHALL perform AI-based relevance re-ranking of items before selecting the top N for blog generation.

#### Scenario: Items re-ranked before selection
- **WHEN** `horizon-blog` processes a list of items
- **THEN** items are re-ranked by the AI relevance ranker before the `max_posts` limit is applied

#### Scenario: Ranking failure falls back to original order
- **WHEN** the AI relevance ranking call fails
- **THEN** the original order of items from the input file is used and a warning is printed
