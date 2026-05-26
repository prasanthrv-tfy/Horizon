## Context

Phase 2 left `horizon-publish` at a dedup-filtered candidate list with no actual Webflow writes. `WebflowPublisher.add_draft` raises `NotImplementedError`. Phase 3 closes the loop: for each candidate post, the CLI converts Markdown to HTML, generates SEO fields via AI, and POSTs a draft to Webflow.

The Webflow Staged Items create endpoint:
`POST /v2/collections/{collection_id}/items` with body:
```json
{
  "fieldData": {
    "name": "<title>",
    "slug": "<slug>",
    "meta-title": "<SEO title>",
    "meta-description": "<SEO description>",
    "content": "<rich HTML>",
    "published-date": "<ISO 8601>",
    "min-read": "<N min read>",
    "featured-on-top": "false"
  },
  "isArchived": false,
  "isDraft": true
}
```

## Goals / Non-Goals

**Goals:**
- Convert Markdown to HTML using Python-Markdown
- Compute reading time from character count (average ~200 wpm, ~5 chars/word)
- Generate SEO title (≤60 chars) and meta description (≤160 chars) via one AI call per post
- Load post metadata (title, slug, tags, url, date) from front matter of generated `.md` files
- Implement `WebflowPublisher.add_draft` — POST payload, return Webflow item ID
- Wire the full push loop into `horizon-publish` CLI with per-post logging

**Non-Goals:**
- Publishing drafts live (manual review in Webflow before going live)
- Updating or editing already-existing Webflow items
- Retry logic beyond a single attempt per post (failures are logged, not retried)
- `publish_draft` and `delete_item` (still `NotImplementedError` — not needed yet)

## Decisions

### 1. One AI call per post for SEO

SEO generation is a small, fast prompt (title + body → two short strings). Batching all posts in one call would complicate parsing and increase blast radius on failure. One call per post is simpler and lets the CLI log progress item by item.

*Alternative*: batch all posts in one AI call — rejected due to parsing complexity and harder per-post error handling.

### 2. `PostLoader` reads front matter with regex, not a YAML parser

The front matter in generated posts is simple (flat key-value, no nesting). A lightweight regex parser avoids adding `pyyaml` as a dependency. Falls back gracefully on malformed front matter.

*Alternative*: `pyyaml` — rejected to avoid a new dependency for a simple use case.

### 3. Reading time from character count

Formula: `ceil(char_count / (200 * 5))` minutes (200 wpm × ~5 chars/word). Applied to the raw Markdown text before HTML conversion to avoid counting HTML tags.

### 4. Slug derived from front matter, falls back to filename stem

The generated posts already have slugs encoded in their filenames (`YYYY-MM-DD-<slug>-<lang>.md`). `PostLoader` reads the front matter `slug:` field first; if absent, it strips the date prefix and language suffix from the filename.

### 5. Sequential posting with per-post error handling

The CLI iterates kept posts one by one. A failed `add_draft` (non-2xx from Webflow) logs an error and continues rather than aborting the run. This prevents one bad post from blocking the rest.

## Risks / Trade-offs

- **AI SEO cost** — One AI call per post. For 10 posts this is trivial; at scale it adds latency and token cost.  
  → Acceptable for now. Can batch in a future phase.

- **Webflow field names are hardcoded** — If the collection uses non-standard field slugs, `add_draft` will create malformed items silently.  
  → Mitigation: log the Webflow API response body on non-2xx so the user can diagnose field errors.

- **`markdown` extension set** — Python-Markdown with default extensions. Tables and fenced code blocks require explicit extensions; missing ones render as plain text.  
  → Use `extra` extension bundle which covers tables, fenced code, footnotes, etc.

## Open Questions

- None for Phase 3. The Webflow field mapping is established in the master spec.
