## Context

Horizon is an upstream open-source project. We've added blog generation on top of it by modifying upstream files directly. The main conflict surface is `src/orchestrator.py::HorizonOrchestrator.run()` — every upstream feature lands there. Our blog additions grew that file by 160+ lines and scattered blog concerns across `models.py`, `ai/prompts.py`, and `ai/blog_writer.py`.

The goal is to move all blog code into `src/blog/` so upstream merges only touch ~5 lines in 2 files.

## Goals / Non-Goals

**Goals:**
- All blog-specific code lives in `src/blog/` — zero blog logic in upstream files
- `horizon` pipeline writes `important_items.json`; `horizon-blog` reads it — fully decoupled execution
- `BlogConfig` lives in `src/blog/models.py`; `Config` gets one optional field
- Upstream files (`orchestrator.py`, `ai/prompts.py`, `ai/blog_writer.py`) revert to near-original shape
- Existing blog output (paths, formats, Jekyll front matter) is unchanged

**Non-Goals:**
- Changing blog post content or format
- Adding new blog features
- Modifying the enricher or summarizer pipeline stages

## Decisions

### 1. File-based decoupling over in-process hooks

**Decision**: `horizon` saves `important_items.json` to `data/pipeline-output/`; `horizon-blog` reads it as its input.

**Why**: A hook/callback system inside the orchestrator would still require modifying upstream code every time the interface changes. A file is a stable, inspectable interface — it also lets blog generation be re-run without re-running the expensive pipeline.

**Alternative considered**: Subclassing `HorizonOrchestrator` to override `run()`. Rejected because subclassing still requires importing and coupling to the orchestrator's internals, and Python method resolution makes it fragile across upstream refactors.

---

### 2. New `src/blog/` module (not extending `src/ai/`)

**Decision**: Create `src/blog/` as a sibling package to `src/ai/`, not as additions inside `src/ai/`.

**Why**: Blog generation is an application-level concern (reads config, writes files, exposes a CLI), whereas `src/ai/` is a utility layer (clients, prompts, token tracking). Mixing them blurs the boundary and makes the `src/ai/` folder harder to sync with upstream.

**Module layout**:
```
src/blog/
  __init__.py
  models.py    ← BlogConfig, BlogPost
  prompts.py   ← RELEVANCE_RANKING_*, BLOG_POST_*
  writer.py    ← BlogWriter (moved from src/ai/blog_writer.py)
  runner.py    ← CLI entry point + orchestration logic
```

---

### 3. `BlogConfig` as optional field on upstream `Config`

**Decision**: Add `blog: Optional[BlogConfig] = None` to `src/models.py::Config`. `BlogConfig` is defined in `src/blog/models.py` and imported there.

**Why**: The `horizon-blog` CLI needs to share AI provider settings (`ai.*`) and output paths with the rest of the system — it reads the same `data/config.json`. Adding one optional field to `Config` is the minimal upstream touch; Pydantic ignores missing optional fields so existing configs need no changes.

**Alternative considered**: A separate `blog_config.json`. Rejected — users would need to maintain two config files with duplicated AI provider settings.

---

### 4. `important_items.json` written before enrichment

**Decision**: Save `important_items.json` immediately after the threshold filter + topic dedup step, before enrichment runs.

**Why**: `BlogWriter` does its own DuckDuckGo web searches for context — it doesn't depend on enricher output. Saving pre-enrichment keeps the file small and the two AI passes independent. If saved post-enrichment, `horizon-blog` would silently depend on enrichment having run, creating a hidden ordering constraint.

---

### 5. `json_mode` changes in `src/ai/client.py` stay

**Decision**: Keep the `json_mode: bool = True` parameter added to all AI client `complete()` methods.

**Why**: `BlogWriter` needs to make non-JSON (Markdown) completions. This is an additive, backwards-compatible change — all existing callers pass no argument and get the original JSON behaviour. Low merge risk.

## Risks / Trade-offs

- **Stale `important_items.json`**: `horizon-blog` reads whatever is in the file — if the pipeline hasn't run recently, the blog posts will be based on old data. Mitigation: document that `horizon` should run before `horizon-blog`; optionally emit a warning if the file is older than 48h.

- **Import of upstream `CONCEPT_EXTRACTION_*` prompts**: `BlogWriter` uses `CONCEPT_EXTRACTION_SYSTEM/USER` from `src/ai/prompts.py` (upstream). If upstream renames or removes these, `src/blog/writer.py` breaks. Mitigation: these prompts are stable and used by the enricher too — low risk. If they're ever removed upstream, copy them into `src/blog/prompts.py`.

- **`Config` import coupling**: `src/models.py` will import `BlogConfig` from `src/blog/models.py`. This means the upstream `models.py` gains a dependency on our module. Mitigation: use `TYPE_CHECKING` guard or lazy import to keep it lightweight; the single-line addition is easy to re-apply after merges.

## Migration Plan

1. Create `src/blog/` with all moved code
2. Update imports in moved files
3. Strip blog code from `orchestrator.py`, `ai/prompts.py`; delete `ai/blog_writer.py`
4. Add `save_important_items()` call in `orchestrator.py`
5. Update `models.py` — remove fields from `FilteringConfig`, add `BlogConfig` import + field to `Config`
6. Add `horizon-blog` entry point to `pyproject.toml`
7. Test: run `horizon` to produce `important_items.json`, then `horizon-blog` to generate posts

No rollback complexity — this is a pure refactor with no data migrations or schema changes.

## Open Questions

- Should `horizon-blog` accept the input file path as a CLI argument (e.g. `horizon-blog --input data/pipeline-output/important_items.json`) or always use the fixed default path?
