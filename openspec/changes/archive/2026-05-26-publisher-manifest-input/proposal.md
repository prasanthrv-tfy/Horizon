## Why

The publisher currently depends on `docs/_posts/` Jekyll files for all post metadata (title, score, tags, URL), but the score written there comes from the upstream pipeline's AI relevance score rather than the blog generator's own multi-dimensional `weighted_sum`. Removing the Jekyll intermediary and having the generator emit a structured JSON manifest means the publisher always works from blog-accurate data without the `docs/_posts/` coupling.

## What Changes

- Generator **stops writing** to `docs/_posts/` entirely **BREAKING**
- Generator writes a `posts.json` manifest per profile run to `artifacts/blog-posts/{profile}/posts.json`, containing an array of post metadata objects (title, slug, score, tags, url, published_at, language, profile, filename)
- Score in the manifest is the blog generator's own score: `weighted_sum` for profiles with gate paths, `ai_score` for legacy profiles
- Publisher reads `artifacts/blog-posts/*/posts.json` manifests instead of `docs/_posts/**/*.md`
- `loader.py` is rewritten to accept a manifest entry + base directory instead of a Jekyll markdown path
- `deduplicator.py` is updated to work with manifest entries instead of `Path` objects

## Capabilities

### New Capabilities
- `blog-posts-manifest`: Generator writes a `posts.json` manifest per profile run to `artifacts/blog-posts/{profile}/` with structured post metadata including the blog generator's score

### Modified Capabilities
- `horizon-publish-cli`: Input source changes from `docs/_posts/**/*.md` to `artifacts/blog-posts/*/posts.json` manifests; post metadata is read from JSON rather than parsed Jekyll front matter

## Impact

- `src/blog/generator/runner.py` — `generate_and_save_posts()` and its call sites
- `src/blog/publisher/runner.py` — input glob, `_dump_html()`, main loop
- `src/blog/publisher/loader.py` — full rewrite (Jekyll parser → JSON + MD loader)
- `src/blog/publisher/deduplicator.py` — signature change (Path list → entry list)
- `docs/_posts/` directory — no longer written; downstream GitHub Pages consumers would need to adapt
