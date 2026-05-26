## 1. PostLoader: read generated post files

- [x] 1.1 Create `src/blog/publisher/loader.py` with `load_post(path: Path) -> dict`
- [x] 1.2 Parse front matter fields: `title`, `slug`, `original_url`, `date`, `tags` using regex (no external YAML parser)
- [x] 1.3 Fall back to filename-derived values when front matter fields are absent (slug from stem strip, date from filename prefix, empty tags/url)
- [x] 1.4 Read the body (content after front matter) and store as `markdown` key in the returned dict

## 2. Markdown → HTML converter and reading time

- [x] 2.1 Create `src/blog/publisher/converter.py` with `convert_markdown(text: str) -> str` using `markdown.markdown(text, extensions=["extra"])`
- [x] 2.2 Implement `reading_time(text: str) -> str` — `ceil(len(text) / 1000)` minutes, return `"N min read"`
- [x] 2.3 Call `convert_markdown` and `reading_time` inside `load_post` and store results as `html` and `reading_time` keys

## 3. SEO generation

- [x] 3.1 Create `src/blog/publisher/seo.py` with `async generate_seo(title: str, markdown: str, ai_client) -> dict`
- [x] 3.2 Prompt the AI client to return JSON `{"seo_title": "...", "seo_description": "..."}` with ≤60 and ≤160 char constraints stated
- [x] 3.3 Parse AI response; truncate `seo_title` to 60 chars and `seo_description` to 160 chars if exceeded
- [x] 3.4 On any exception from the AI client, log a warning and return `{"seo_title": title[:60], "seo_description": ""}`

## 4. WebflowPublisher: add_draft

- [x] 4.1 Implement `WebflowPublisher.add_draft(item: dict) -> str` — build the Webflow CMS payload from the post dict fields
- [x] 4.2 POST to `POST /v2/collections/{collection_id}/items`; return the `id` field from the response JSON
- [x] 4.3 Raise `RuntimeError` with status code and response body on non-2xx response

## 5. CLI: wire the full push pipeline

- [x] 5.1 In `runner.py`, iterate over kept posts: call `load_post`, `generate_seo`, `publisher.add_draft` for each
- [x] 5.2 Log success per post: `✓ <title> → <webflow_item_id>`
- [x] 5.3 Log failure per post and continue: `✗ <title> — <error message>`
- [x] 5.4 Print a run summary at the end: `Pushed: N  |  Skipped (duplicates): N  |  Failed: N`
- [x] 5.5 Replace the Phase 2 "would publish" listing with the actual push loop

## 6. Verification

- [x] 6.1 Write unit tests for `load_post` covering complete front matter and missing field fallbacks
- [x] 6.2 Write unit tests for `convert_markdown` (basic rendering) and `reading_time` (short and long posts)
- [x] 6.3 Run `uv run pytest` — all tests must pass
- [x] 6.4 Update `CLAUDE.md` to reflect that `horizon-publish` now pushes real drafts
