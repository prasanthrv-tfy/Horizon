## Why

Blog generation code was added directly into upstream files (`orchestrator.py`, `models.py`, `ai/prompts.py`), making future upstream merges error-prone — `orchestrator.py` alone grew by 160+ lines. Consolidating all blog logic into a dedicated `src/blog/` module reduces the upstream diff to ~5 lines across 2 files, while preserving all existing blog generation functionality.

## What Changes

- **New** `src/blog/` module — all blog-specific code moves here (no functionality removed)
- **Moved** `src/ai/blog_writer.py` → `src/blog/writer.py`
- **Moved** `BlogPost` dataclass → `src/blog/models.py`
- **Moved** blog prompts (`RELEVANCE_RANKING_*`, `BLOG_POST_*`) from `src/ai/prompts.py` → `src/blog/prompts.py`
- **Moved** `_rank_by_relevance()` and `_generate_blog_posts()` from `src/orchestrator.py` → `src/blog/runner.py`
- **Moved** `max_blog_posts` and `topics` from `FilteringConfig` → new `BlogConfig` in `src/blog/models.py`
- **New** `horizon-blog` CLI entry point — reads `data/pipeline-output/important_items.json`, runs ranking + blog generation independently
- **Added** `data/pipeline-output/important_items.json` as the interface file: written by `horizon`, read by `horizon-blog`
- **Added** optional `blog: Optional[BlogConfig] = None` field to `Config` in `src/models.py`
- **Reverted** `src/orchestrator.py` toward upstream shape — debug dumps removed, blog calls removed, `save_important_items()` added (~5 lines)
- **Reverted** `src/ai/prompts.py` toward upstream shape — blog prompts removed (moved, not deleted)

## Capabilities

### New Capabilities

- `blog-generation`: Standalone blog post generation — reads scored content items from a pipeline output file, optionally re-ranks by AI relevance, generates per-item Markdown blog posts in one or more languages, writes them to `data/blog-posts/` and `docs/_posts/`

### Modified Capabilities

<!-- None — upstream pipeline external behavior is unchanged -->

## Impact

- `src/blog/` (new): receives all blog-specific code — `BlogConfig`, `BlogPost`, blog prompts, `BlogWriter`, relevance ranker, and the `horizon-blog` CLI runner
- `src/orchestrator.py`: blog methods and debug dumps moved out; ~5 lines added to save `important_items.json` after threshold filtering
- `src/models.py`: `max_blog_posts` and `topics` moved to `BlogConfig`; one optional `blog` field added to `Config`
- `src/ai/prompts.py`: blog prompts moved to `src/blog/prompts.py`; file reverted to upstream shape
- `src/ai/blog_writer.py`: moved to `src/blog/writer.py`; original file deleted
- `pyproject.toml`: `horizon-blog` entry point added
- No changes to scraper, enricher, summarizer, or delivery logic
- No API or webhook interface changes