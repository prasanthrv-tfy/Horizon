# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (use uv)
uv sync
uv sync --extra dev        # includes pytest
uv sync --extra openbb     # optional financial-news source

# Run the pipeline
uv run horizon             # default 24h window
uv run horizon --hours 48

# Generate blog posts (run after horizon)
uv run horizon-blog                          # reads artifacts/pipeline-output/important_items.json
uv run horizon-blog --profile engineer       # run a specific profile
uv run horizon-blog --profile all            # run all profiles
uv run horizon-blog --rank-only              # score/rank without generating posts
uv run horizon-blog --all-posts              # generate posts for all gate-passing items (ignores max_posts)
uv run horizon-blog --max-posts 6            # override max_posts from config at runtime
uv run horizon-blog --items 3,7,15           # generate posts for specific row numbers (bypasses gates)

# Other entry points
uv run horizon-wizard      # interactive config setup
uv run horizon-mcp         # start MCP server
uv run horizon-webhook     # test/send webhook notifications

# Tests
uv run pytest              # all tests
uv run pytest tests/test_analyzer.py          # single file
uv run pytest tests/test_analyzer.py::test_fn  # single test
uv run pytest -x           # stop on first failure
```

## Architecture

Horizon is a linear pipeline coordinated by `src/orchestrator.py::HorizonOrchestrator.run()`. Each stage produces a transformed list of `ContentItem` objects:

```
Fetch → URL Dedup → AI Score → Threshold Filter → Topic Dedup → Save → Enrich → Summarize → Deliver
```

**Key stages:**
- **Fetch** (`orchestrator.fetch_all_sources`): all scrapers run concurrently via `asyncio.gather` sharing a single `httpx.AsyncClient`.
- **URL Dedup** (`merge_cross_source_duplicates`): normalises URLs, merges same-URL items across sources, keeps the richest content.
- **AI Score** (`src/ai/analyzer.py::ContentAnalyzer`): sends each item to the LLM and receives a JSON with `score` (0–10), `reason`, `summary`, `tags`. Retries via `tenacity`.
- **Topic Dedup** (`merge_topic_duplicates`): one AI call over all titles/summaries to detect semantically identical stories; drops lower-scored duplicates.
- **Save** (`orchestrator._save_important_items`): serialises `important_items` to `artifacts/pipeline-output/important_items.json` for consumption by `horizon-blog`.
- **Enrich** (`src/ai/enricher.py::ContentEnricher`): two-step AI pass — first call identifies concepts needing explanation, second call synthesises background from DuckDuckGo search results. Stores results in `item.metadata` under keys like `title_en`, `detailed_summary_zh`, `background_en`, `community_discussion_zh`, `sources`.
- **Summarize** (`src/ai/summarizer.py::DailySummarizer`): purely programmatic Markdown rendering (no LLM call). Reads fields from `item.metadata` populated by the enricher.
- **Deliver**: saves to `data/summaries/`, copies to `docs/_posts/` for GitHub Pages, optionally emails and/or posts to webhooks.

### Data model

`ContentItem` (Pydantic, `src/models.py`) is the universal unit throughout the pipeline:
- `id`: `"{source}:{subtype}:{native_id}"` — stable identifier
- `ai_score / ai_reason / ai_summary / ai_tags`: set by the analyzer
- `metadata: Dict[str, Any]`: open-ended bag used by scrapers for engagement signals and by the enricher for translated/enriched fields

### AI client abstraction

`src/ai/client.py::create_ai_client(config)` is the factory. All providers share the same `complete(system, user) -> str` interface:
- **`AnthropicClient`** — Anthropic SDK
- **`OpenAIClient`** — covers OpenAI, Ollama, DeepSeek, Alibaba/Qwen, Doubao, MiniMax (handles per-provider quirks like temperature clamping and missing `response_format`)
- **`AzureOpenAIClient`** — Azure OpenAI; handles `max_tokens` vs `max_completion_tokens` fallback
- **`GeminiClient`** — Google Gemini via `google-genai`

Token usage is tracked in-memory by `src/ai/tokens.py` and printed after each run.

### Adding a new scraper

1. Create `src/scrapers/your_source.py` extending `BaseScraper` and implementing `fetch(since: datetime) -> List[ContentItem]`.
2. Add a config model to `src/models.py` and add the field to `SourcesConfig`.
3. Instantiate and register the scraper in `orchestrator.fetch_all_sources`.

### MCP server

`src/mcp/service.py::HorizonPipelineService` exposes each pipeline stage as an individually-callable method (`fetch_items`, `score_items`, `filter_items`, `enrich_items`, `generate_summary`, `run_pipeline`). Stage outputs are persisted as JSON to `data/mcp-runs/<run_id>/` so agents can inspect intermediate results. The FastMCP server in `src/mcp/server.py` wraps these methods as tools.

### Blog generation module

`src/blog/` is a self-contained module added on top of upstream Horizon. It is intentionally isolated so upstream merges only touch ~5 lines in `src/orchestrator.py` and `src/models.py`.

- **`src/blog/models.py`** — `ScoringDimension`, `ScoredItem`, `BlogPost`, `BlogConfig`.
- **`src/blog/prompts.py`** — `ITEM_SCORING_SYSTEM/USER` (multi-dim scoring) and `RELEVANCE_RANKING_*` (legacy fallback).
- **`src/blog/writer.py`** — `BlogWriter`: accepts a `BlogPromptProfile`, does DuckDuckGo web searches using the profile's research prompts, then generates a Markdown blog post via the AI client.
- **`src/blog/runner.py`** — `horizon-blog` entry point: loads `artifacts/pipeline-output/important_items.json`, scores items per profile using `score_items_for_profile()`, applies gate paths, selects top N (or all with `--all-posts`) by weighted sum, calls `BlogWriter` for each, writes to `artifacts/blog-posts/{profile}/` and `docs/_posts/{profile}/`. Run logs written to `artifacts/blog-runs/YYYY-MM-DD-{profile}.json`. At the end of each run, auto-regenerates `artifacts/ranking_results.md` with the full scoring table and cross-profile comparison.
- **`src/blog/profiles/`** — prompt profile subpackage (see below).

#### Multi-dimensional scoring and gate paths

Profiles with `scoring_dimensions` use gate-based filtering instead of pure ranking. `score_items_for_profile()` sends all items to the LLM in one call, getting a score (0–10) + reason per dimension per item. An item is included if it passes **all** dimensions in **any** gate path (AND within path, OR across paths). Included items are ranked by a per-path weighted sum.

`ScoringDimension` fields: `name`, `description`, `gate_threshold`, `path_a_weight`, `path_b_weight`, `anchors`. Dimensions with `path_x_weight=0` are still scored (appear in logs) but don't contribute to that path's weighted sum.

#### Prompt profiles

Each profile is a Python file in `src/blog/profiles/` exporting a `PROFILE = BlogPromptProfile(...)`. Adding a new profile = adding one file and one import in `__init__.py`. Human-readable descriptions of all profiles, gate paths, scoring dimensions, and score milestones live in `docs/blog-profiles.md` — update it when profile code changes.

| Profile | File | Audience | Gate paths |
|---|---|---|---|
| `news` | `profiles/news.py` | General tech readers | Single path: significance + newsworthiness + narrative_clarity |
| `engineer` | `profiles/engineer.py` | ML/MLOps engineers | Path A (research): ml_eng_rel >= 7 AND substance >= 7; Path B (deployable): ml_eng_rel >= 7 AND substance >= 5 AND applicability >= 6 |

The engineer profile's `ai_ecosystem_significance` dimension is **not** a gate — it contributes only to Path B's weighted sum (weight 0.15) to rank major provider releases above niche ones.

`BlogPromptProfile` bundles: `blog_system`, `blog_user`, `research_system`, `research_user`, `scoring_dimensions`, `gate_paths`. The research prompts control web search queries — the news profile searches for concept explanations, the engineer profile targets papers, benchmarks, and implementations.

Blog config is optional in `data/config.json`:
```json
"blog": {
  "max_posts": 4,
  "topics": [],
  "output_dir": "artifacts/blog-posts",
  "prompt_profile": "news",
  "audience_context": "",
  "platform_context": ""
}
```

Set `"prompt_profile": "all"` to run all registered profiles in one invocation; outputs land in separate subdirectories for side-by-side comparison. `max_posts` is overridden to unlimited by `--all-posts` at runtime.

### Configuration

`data/config.json` is validated by Pydantic against `src/models.py::Config`. Any string value supports `${ENV_VAR}` interpolation (handled in `StorageManager.load_config` before Pydantic sees the data). All API keys are referenced by env-var name, not stored inline.

The prompt strings that drive AI scoring and enrichment live in `src/ai/prompts.py`. Blog-specific prompts live in `src/blog/prompts.py`.