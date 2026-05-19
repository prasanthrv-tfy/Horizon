## 1. Create src/blog/ module scaffold

- [x] 1.1 Create `src/blog/__init__.py`
- [x] 1.2 Create `src/blog/models.py` with `BlogPost` dataclass (moved from `src/ai/blog_writer.py`) and `BlogConfig` Pydantic model (with `max_posts: int = 4`, `topics: List[str] = []`, `output_dir: str = "data/blog-posts"`)
- [x] 1.3 Create `src/blog/prompts.py` with `RELEVANCE_RANKING_SYSTEM`, `RELEVANCE_RANKING_USER`, `BLOG_POST_SYSTEM`, `BLOG_POST_USER` (moved from `src/ai/prompts.py`)

## 2. Move BlogWriter into src/blog/

- [x] 2.1 Create `src/blog/writer.py` by moving `BlogWriter` class from `src/ai/blog_writer.py`
- [x] 2.2 Update imports in `src/blog/writer.py` — blog prompts from `src.blog.prompts`, `CONCEPT_EXTRACTION_*` from `src.ai.prompts`, `BlogPost` from `src.blog.models`
- [x] 2.3 Delete `src/ai/blog_writer.py`

## 3. Create src/blog/runner.py (CLI entry point)

- [x] 3.1 Create `src/blog/runner.py` with a `main()` function as the `horizon-blog` entry point
- [x] 3.2 Implement `load_important_items(path)` — reads `data/pipeline-output/important_items.json`, raises a clear error if missing or empty
- [x] 3.3 Move `_rank_by_relevance()` logic from `src/orchestrator.py` into `runner.py` as a standalone async function
- [x] 3.4 Move `_generate_blog_posts()` logic from `src/orchestrator.py` into `runner.py`, reading output paths from `BlogConfig`
- [x] 3.5 Wire `main()` to: load config → load items → rank → select top N → generate posts

## 4. Update upstream files (minimal changes)

- [x] 4.1 Add `save_important_items(items)` call in `src/orchestrator.py` after topic dedup, writing to `data/pipeline-output/important_items.json` (create dir if needed)
- [x] 4.2 Remove `_rank_by_relevance()`, `_generate_blog_posts()`, `_debug_dump()`, and all their call sites from `src/orchestrator.py`
- [x] 4.3 Remove `RELEVANCE_RANKING_SYSTEM`, `RELEVANCE_RANKING_USER`, `BLOG_POST_SYSTEM`, `BLOG_POST_USER` from `src/ai/prompts.py`
- [x] 4.4 Remove `max_blog_posts` and `topics` fields from `FilteringConfig` in `src/models.py`
- [x] 4.5 Add `from src.blog.models import BlogConfig` import and `blog: Optional[BlogConfig] = None` field to `Config` in `src/models.py`

## 5. Register new CLI entry point

- [x] 5.1 Add `horizon-blog = "src.blog.runner:main"` to `[project.scripts]` in `pyproject.toml`

## 6. Verify

- [x] 6.1 Run `uv run horizon` and confirm `data/pipeline-output/important_items.json` is written
- [x] 6.2 Run `uv run horizon-blog` and confirm blog posts appear in `data/blog-posts/` and `docs/_posts/`
- [x] 6.3 Confirm `uv run horizon` no longer calls any blog generation code
- [x] 6.4 Confirm running with no `blog` section in `config.json` works without error
