## 1. Restructure: Move generator files

- [x] 1.1 Create `src/blog/generator/` directory with `__init__.py`
- [x] 1.2 Move `runner.py`, `writer.py`, `scorer.py`, `enricher.py`, `fetcher.py`, `loader.py`, `reporter.py`, `prompts.py` from `src/blog/` to `src/blog/generator/`
- [x] 1.3 Update all relative imports inside moved files (`from .X` → sibling references within `generator/`; shared imports like `from .models` → `from ..models`)
- [x] 1.4 Update `pyproject.toml` `horizon-blog` entry point to point to `src.blog.generator.runner:main`
- [x] 1.5 Verify `uv run horizon-blog --rank-only` runs without ImportError

## 2. Config: PublisherConfig model

- [x] 2.1 Add `PublisherConfig` Pydantic model to `src/blog/models.py` with `collection_id: str = ""` and `deduplication_time_window: int = 14`
- [x] 2.2 Add `publisher: PublisherConfig = PublisherConfig()` field to `BlogConfig`
- [x] 2.3 Verify existing configs without a `publisher` key still load without validation errors

## 3. Publisher: Abstract base class

- [x] 3.1 Create `src/blog/publisher/` directory with `__init__.py`
- [x] 3.2 Create `src/blog/publisher/publisher.py` with abstract `Publisher(ABC)` class
- [x] 3.3 Define abstract methods: `add_draft`, `list_items`, `get_item`, `publish_draft`, `delete_item` with correct signatures and docstrings

## 4. Publisher: WebflowPublisher implementation

- [x] 4.1 Create `src/blog/publisher/webflow.py` with `WebflowPublisher(Publisher)` class
- [x] 4.2 Implement `__init__` that accepts `token: str` and `collection_id: str`, initialises `httpx.AsyncClient` with `Authorization: Bearer <token>` header
- [x] 4.3 Implement all five methods as stubs raising `NotImplementedError` with a descriptive message (e.g. `"Implemented in Phase 2"`)

## 5. CLI: horizon-publish entry point

- [x] 5.1 Create `src/blog/publisher/runner.py` with a `main()` function
- [x] 5.2 Implement `WEBFLOW_TOKEN` check — exit with error if missing
- [x] 5.3 Implement post discovery: scan `artifacts/blog-posts/**/*.md` and collect file paths
- [x] 5.4 Print dry-run summary: count of posts found and their filenames, with a clear "[DRY RUN]" notice
- [x] 5.5 Register `horizon-publish = "src.blog.publisher.runner:main"` in `pyproject.toml` under `[project.scripts]`
- [x] 5.6 Verify `uv run horizon-publish` runs and prints the dry-run output

## 6. Verification

- [x] 6.1 Run `uv run pytest` — all existing tests must pass
- [x] 6.2 Update `CLAUDE.md` with `uv run horizon-publish` command and updated module layout
