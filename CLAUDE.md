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
uv run horizon-blog        # reads data/pipeline-output/important_items.json

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
- **Save** (`orchestrator._save_important_items`): serialises `important_items` to `data/pipeline-output/important_items.json` for consumption by `horizon-blog`.
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

- **`src/blog/models.py`** — `BlogPost` dataclass and `BlogConfig` Pydantic model (`max_posts`, `topics`, `output_dir`).
- **`src/blog/prompts.py`** — blog-specific prompts (`RELEVANCE_RANKING_*`, `BLOG_POST_*`).
- **`src/blog/writer.py`** — `BlogWriter`: for each `ContentItem`, extracts concepts, does DuckDuckGo web searches for context, then generates a Markdown blog post via the AI client.
- **`src/blog/runner.py`** — `horizon-blog` entry point: loads `data/pipeline-output/important_items.json`, re-ranks by AI relevance, selects top N, calls `BlogWriter`, writes output to `data/blog-posts/` and `docs/_posts/` with Jekyll front matter.

Blog config is optional in `data/config.json`:
```json
"blog": {
  "max_posts": 4,
  "topics": [],
  "output_dir": "data/blog-posts"
}
```

### Configuration

`data/config.json` is validated by Pydantic against `src/models.py::Config`. Any string value supports `${ENV_VAR}` interpolation (handled in `StorageManager.load_config` before Pydantic sees the data). All API keys are referenced by env-var name, not stored inline.

The prompt strings that drive AI scoring and enrichment live in `src/ai/prompts.py`. Blog-specific prompts live in `src/blog/prompts.py`.