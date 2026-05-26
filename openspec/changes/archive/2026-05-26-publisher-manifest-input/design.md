## Context

The blog generator (`horizon-blog`) writes posts to two locations: `artifacts/blog-posts/{profile}/` (raw markdown) and `docs/_posts/{profile}/` (Jekyll front matter + markdown body). The publisher (`horizon-publish`) reads exclusively from `docs/_posts/`, using the Jekyll front matter to retrieve per-post metadata. The score stored in that front matter is `ContentItem.ai_score` — the upstream pipeline's relevance score — not the blog generator's own `weighted_sum` computed by the multi-dimensional scoring system. Removing the Jekyll intermediary eliminates the score mismatch and reduces the publish pipeline to a single input source.

## Goals / Non-Goals

**Goals:**
- Generator emits a `posts.json` manifest per profile run alongside existing `.md` files in `artifacts/blog-posts/`
- Manifest score reflects the blog generator's own score (`weighted_sum` for gate profiles, `ai_score` for legacy profiles)
- Publisher reads manifest + paired `.md` files; no longer reads `docs/_posts/`
- Generator stops writing to `docs/_posts/`

**Non-Goals:**
- Changing the Webflow API integration or SEO generation
- Supporting multiple manifest formats (only JSON)
- Migrating previously written `docs/_posts/` files

## Decisions

### 1. Single combined manifest per profile run, not per-post sidecars

A single `posts.json` array per profile keeps the output directory clean (two files per run: N `.md` + one `.json`) and is simpler to scan than per-post `.json` sidecars. The publisher discovers manifests via `artifacts/blog-posts/*/posts.json`.

*Alternative considered*: per-post `.json` sidecar (same basename, `.json` extension). Rejected — doubles the file count, requires pairing logic, no structural benefit over a manifest array.

### 2. `filename` field in manifest entry links to the paired `.md`

Each entry stores the basename of its markdown file (e.g. `2026-05-25-my-slug-en.md`). The publisher resolves the full path as `manifest_dir / entry["filename"]`. This avoids re-deriving slugs and keeps loader logic simple.

### 3. Score selection: `weighted_sum` for gate profiles, `ai_score` for legacy

When `scoring_dimensions` are configured, `ScoredItem.weighted_sum` is the blog-level score and is passed to `generate_and_save_posts` via a `blog_scores: dict[str, float]` parameter. For legacy profiles without dimensions, the parameter is absent and `BlogPost.score` (which holds `ai_score`) is used unchanged.

*Alternative considered*: always use `ai_score` as a baseline and add a separate `blog_score` field. Rejected — redundant fields; callers (publisher sort, deduplicator) only need one score signal.

### 4. `loader.py` accepts a manifest entry dict + base_dir

The existing `load_post(path: Path)` signature is replaced with `load_post(entry: dict, base_dir: Path)`. This is a clean break — no backward-compatible shim needed since `loader.py` is only called from `publisher/runner.py`.

### 5. Remove `docs/_posts/` write from generator

The Jekyll write block in `generate_and_save_posts()` is removed. GitHub Pages was the only consumer; the project does not actively serve GitHub Pages as a production output.

## Risks / Trade-offs

- **`docs/_posts/` removal is a breaking change** → Any external tooling or CI that reads `_posts/` will break. Mitigation: document in commit message; the directory is not published externally.
- **Manifest is overwritten each run** → Re-running `horizon-blog` replaces `posts.json` with only the latest posts. Previously generated posts from older runs are no longer in the manifest. Mitigation: acceptable since the publisher is typically run immediately after `horizon-blog`; the `.md` files themselves are preserved.
- **`deduplicator.py` interface change** → Code outside `publisher/runner.py` that calls `deduplicate_posts` would break. Mitigation: only one call site exists.

## Migration Plan

1. Run `uv run horizon-blog` — generates new `posts.json` alongside `.md` files; no longer writes `_posts/`
2. Run `uv run horizon-publish` — reads from `artifacts/blog-posts/`
3. Delete stale `docs/_posts/` directory manually if desired

No rollback strategy required — change is local to `src/blog/`.

## Open Questions

None.
