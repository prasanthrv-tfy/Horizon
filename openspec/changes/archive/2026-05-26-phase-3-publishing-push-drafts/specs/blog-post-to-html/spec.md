## ADDED Requirements

### Requirement: Markdown to HTML conversion
The system SHALL provide a `convert_markdown(text: str) -> str` function in `src/blog/publisher/converter.py` that converts Markdown to rich HTML using Python-Markdown with the `extra` extension bundle (covers tables, fenced code blocks, footnotes).

#### Scenario: Basic Markdown rendered
- **WHEN** `convert_markdown("# Hello\n\nParagraph")` is called
- **THEN** it SHALL return an HTML string containing `<h1>` and `<p>` tags

#### Scenario: Fenced code block rendered
- **WHEN** input contains a fenced code block (triple backtick)
- **THEN** the output SHALL contain a `<code>` or `<pre>` block

### Requirement: Reading time estimation
The system SHALL provide a `reading_time(text: str) -> str` function in `src/blog/publisher/converter.py` that estimates reading time from the raw Markdown character count and returns a human-readable string (e.g. `"3 min read"`).

#### Scenario: Short post
- **WHEN** the Markdown text is under ~1000 characters
- **THEN** `reading_time` SHALL return `"1 min read"`

#### Scenario: Longer post
- **WHEN** the Markdown text is ~5000 characters
- **THEN** `reading_time` SHALL return `"5 min read"` (approximately)

### Requirement: PostLoader reads generated post files
The system SHALL provide a `load_post(path: Path) -> dict` function in `src/blog/publisher/loader.py` that reads a generated `.md` file and returns a dict with keys: `title`, `slug`, `markdown`, `html`, `tags`, `url`, `published_at`, `reading_time`.

#### Scenario: Post with complete front matter
- **WHEN** the `.md` file has front matter with `title`, `slug`, `original_url`, `date`, `tags`
- **THEN** `load_post` SHALL return a dict with all fields populated from front matter

#### Scenario: Post with missing front matter fields
- **WHEN** some front matter fields are absent
- **THEN** `load_post` SHALL fall back to derived values (slug from filename, date from filename prefix, empty tags list, empty url)
