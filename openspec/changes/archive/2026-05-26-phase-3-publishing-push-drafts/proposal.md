## Why

Phases 1 and 2 scaffolded the publisher and deduplication gate, but `horizon-publish` still makes no actual API calls. Phase 3 completes the pipeline by converting local Markdown posts to rich HTML, generating SEO fields via AI, and pushing each surviving post as a draft to Webflow — making the full `horizon → horizon-blog → horizon-publish` flow functional end-to-end.

## What Changes

- Implement `WebflowPublisher.add_draft(item)` — POST to the Webflow Staged Items API with a fully-formed CMS payload
- Add `MarkdownConverter` in `src/blog/publisher/converter.py` — converts Markdown to HTML using Python-Markdown, computes reading time from character count
- Add `SeoGenerator` in `src/blog/publisher/seo.py` — uses the AI client to generate a short SEO title and meta description from the post content
- Add `PostLoader` in `src/blog/publisher/loader.py` — reads a generated `.md` file from `artifacts/blog-posts/` and reconstructs a `BlogPost`-like dict with `title`, `slug`, `markdown`, `tags`, `url`, `published_at`
- Update `horizon-publish` CLI runner to: load each kept post, convert to HTML, generate SEO fields, call `add_draft`, log created/failed results

## Capabilities

### New Capabilities

- `webflow-add-draft`: `WebflowPublisher.add_draft` fully implemented — builds the Webflow CMS payload and POSTs to the Staged Items API
- `blog-post-to-html`: Markdown → rich HTML conversion + reading-time estimation via `src/blog/publisher/converter.py`
- `publish-seo-generation`: AI-generated SEO title and meta description per post via `src/blog/publisher/seo.py`

### Modified Capabilities

- `blog-publisher-interface`: `add_draft` is no longer a stub — it is fully implemented; `publish_draft` and `delete_item` remain `NotImplementedError`
- `horizon-publish-cli`: The CLI now pushes drafts (load → convert → SEO → add_draft) and logs per-post results (created / failed) instead of just listing candidates

## Impact

- **`src/blog/publisher/webflow.py`**: `add_draft` implemented
- **`src/blog/publisher/converter.py`**: New module — Markdown to HTML, reading time
- **`src/blog/publisher/seo.py`**: New module — AI SEO generation
- **`src/blog/publisher/loader.py`**: New module — reads generated post `.md` files into structured dicts
- **`src/blog/publisher/runner.py`**: Updated to run the full push pipeline for each kept post
- **Dependencies**: `markdown` already present in `pyproject.toml`; AI client already available via `src/ai/client.py`
- **Config**: `WEBFLOW_TOKEN` + `blog.publisher.collection_id` required (already validated in Phase 2)
