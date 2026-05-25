## Context

`src/blog/runner.py` is the `horizon-blog` CLI entry point. Over time it has accumulated five distinct responsibilities: loading pipeline output data, optionally enriching thin items via web search, scoring/ranking items via LLM calls, writing markdown reports and JSON run-logs, and orchestrating the full blog-generation flow. At ~711 lines it has become unwieldy — changes to scoring logic require navigating past reporting code, and testing enrichment requires loading the entire module.

The blog module already has good separation for writer, fetcher, models, prompts, and profiles. The runner is the only outlier.

## Goals / Non-Goals

**Goals:**
- Split runner.py into four new focused modules: `loader`, `enricher`, `scorer`, `reporter`
- Keep `runner.py` as a thin orchestrator (~70 lines) containing only `generate_and_save_posts`, `_run`, and `main`
- Preserve identical external behaviour and CLI interface
- Ensure no circular imports within `src/blog/`

**Non-Goals:**
- No refactoring of logic inside the extracted functions (behaviour-preserving only)
- No changes to `writer.py`, `fetcher.py`, `models.py`, `prompts.py`, or `profiles/`
- No new tests (existing test coverage is the regression guard)
- No changes to `pyproject.toml` entry points

## Decisions

### 1. Four new modules, not one "utils" catch-all

**Decision**: Create four semantically distinct files rather than collapsing everything into a `utils.py`.

**Rationale**: A single utils module would just move the problem. The four groupings have distinct import profiles and concerns:
- `loader` — pure I/O, no AI client
- `enricher` — async, uses fetcher + ContentItem
- `scorer` — async, uses AI client + all scoring models
- `reporter` — pure formatting + file I/O

**Alternative considered**: Two-file split (`io.py` + `scoring.py`). Rejected because it still mixes concerns and the four-file split produces files of roughly equal size (100–200 lines each).

### 2. Keep `runner.py` name (not rename to `orchestrator.py`)

**Decision**: The file stays as `runner.py`; it just shrinks.

**Rationale**: `pyproject.toml` references `src.blog.runner:main`. Renaming would require updating the entry point and any documentation that references the module path. Since the goal is zero-impact refactoring, keeping the name eliminates churn.

### 3. No `__init__.py` re-exports for new modules

**Decision**: New modules are not re-exported from `src/blog/__init__.py`.

**Rationale**: These are internal implementation modules. Exposing them publicly would create an implicit API surface that would resist future reorganisation. `runner.py` imports them directly; nothing else needs to.

## Risks / Trade-offs

- **Import order / circular imports** → Mitigation: All new modules import only from `..models`, `..ai.*`, `..storage`, and `src/blog/models.py`. None import from `runner.py`. Verified by tracing the dependency graph before splitting.
- **Name collision with `src/ai/enricher.py`** → Mitigation: `src/blog/enricher.py` lives in a different package; Python resolves them independently. The names do not collide at runtime but may confuse readers — a brief module docstring clarifying scope addresses this.
- **Missed internal cross-calls** → Mitigation: Extract functions in dependency order (loader first, reporter last) so that any missed call is caught as an `ImportError` at module load time.
