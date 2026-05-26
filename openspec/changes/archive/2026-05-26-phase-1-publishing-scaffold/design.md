## Context

The current `src/blog/` package is a flat module — all generation files sit directly alongside `models.py` and `profiles/`. There is no publishing capability. Phases 2 and 3 need a stable publisher abstraction and a clean module boundary before they can be built.

The orchestrator imports `BlogConfig` from `src/blog/models.py` via a forward reference in `src/models.py`. This is the only external import site; everything else is internal to `src/blog/`.

## Goals / Non-Goals

**Goals:**
- Relocate generation files to `src/blog/generator/` without breaking any existing behaviour
- Define a `Publisher` abstract base class with a clear contract
- Provide a working `WebflowPublisher` skeleton with HTTP client wired up (all methods raise `NotImplementedError`)
- Add `horizon-publish` CLI entry point that reads `artifacts/blog-posts/` and prints a dry-run summary
- Extend `BlogConfig` with `publisher` nested config

**Non-Goals:**
- Any actual Webflow API calls (deferred to Phase 2 and 3)
- Deduplication logic (Phase 2)
- Markdown → HTML conversion (Phase 3)

## Decisions

### 1. Generator as a subpackage, not a rename

Moving files into `src/blog/generator/` rather than renaming the package keeps the top-level `src/blog/` namespace as the stable shared surface. `models.py` and `profiles/` stay at `src/blog/`, so all existing external import sites (`src/models.py`) remain unchanged.

*Alternative considered*: rename `src/blog/` to `src/blog/generator/` entirely — rejected because it would require updating `src/models.py` and every test that imports `BlogConfig`.

### 2. Abstract base class with `abc.ABC`

`Publisher` uses Python's `abc.ABC` / `@abstractmethod` to enforce the interface. This gives clear `TypeError` at instantiation if a method is missing — better than duck typing for a multi-phase build where stubs are intentional.

### 3. WebflowPublisher uses `httpx.AsyncClient`

`httpx` is already a dependency (used throughout the pipeline). Using it for Webflow HTTP calls avoids adding `aiohttp` or `requests`. The client is injected at construction time for testability.

### 4. `PublisherConfig` nested under `BlogConfig`

```python
class PublisherConfig(BaseModel):
    collection_id: str = ""
    deduplication_time_window: int = 14  # days

class BlogConfig(BaseModel):
    ...
    publisher: PublisherConfig = PublisherConfig()
```

Keeps all blog-related config in one place. `collection_id` defaults to empty string so existing configs without a `publisher` key continue to validate.

### 5. `horizon-publish` reads from `artifacts/blog-posts/`

The CLI scans profile subdirectories under `artifacts/blog-posts/` for `*.md` files produced by `horizon-blog`. It does not re-run scoring — it operates on already-generated posts. This keeps the three pipeline stages fully independent.

## Risks / Trade-offs

- **Import churn** — moving files to `generator/` touches every intra-blog relative import (`.writer`, `.scorer`, etc.). Low risk since they all become `..writer`, `..scorer` etc., but must be done carefully.  
  → Mitigation: update all `from .X import` → `from ..X import` within `generator/`, run existing tests after move.

- **`__init__.py` re-exports** — downstream code that does `from src.blog import BlogWriter` will break if `src/blog/__init__.py` doesn't re-export from the new location.  
  → Mitigation: add re-exports in `src/blog/__init__.py` for any symbol that was previously importable from the top level.

## Migration Plan

1. Create `src/blog/generator/` with `__init__.py`
2. Move files: `runner.py`, `writer.py`, `scorer.py`, `enricher.py`, `fetcher.py`, `loader.py`, `reporter.py`, `prompts.py`
3. Update all relative imports inside moved files (`from .X` → `from ..X` where X is a shared file; `from .X` → `from .X` where X is another generator file)
4. Add re-exports to `src/blog/__init__.py` if needed
5. Create `src/blog/publisher/` with `publisher.py`, `webflow.py`, `runner.py`
6. Update `BlogConfig` in `src/blog/models.py` with `PublisherConfig`
7. Register `horizon-publish` in `pyproject.toml`
8. Run `uv run pytest` — all existing tests must pass

Rollback: revert file moves and import changes; no data or config is mutated.

## Open Questions

- None for Phase 1. Webflow field mapping details are resolved in Phase 3.
