# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (use uv)
uv sync
uv sync --extra dev        # includes pytest
uv sync --extra openbb     # optional financial-news source
uv sync --extra upload     # includes truefoundry SDK for artifact upload

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

# Publish blog posts to Webflow (run after horizon-blog)
uv run horizon-publish                       # deduplicates, generates SEO, pushes drafts to Webflow
uv run horizon-publish --publish             # publish live (not drafts)
uv run horizon-publish --generate-image      # generate AI cover images and attach to posts
uv run horizon-publish --dry-run             # preview without writing to Webflow; saves images locally
uv run horizon-publish --max-drafts 5        # override max_drafts from config at runtime

# Upload artifacts to TrueFoundry ML repo
uv run horizon-upload-artifacts --repo-name my-ml-repo        # upload files directly
uv run horizon-upload-artifacts --repo-name my-ml-repo --zip  # upload as a zip archive

# Other entry points
uv run horizon-wizard      # interactive config setup
uv run horizon-mcp         # start MCP server
uv run horizon-webhook     # test/send webhook notifications

# Tests
uv run pytest              # all tests
uv run pytest tests/test_analyzer.py          # single file
uv run pytest tests/test_analyzer.py::test_fn  # single test
uv run pytest -x           # stop on first failure
# Note: tests/test_blog_generator_utils.py has a pre-existing import error (unrelated to blog changes)
# Run with --ignore=tests/test_blog_generator_utils.py to skip it
```

## Architecture

Horizon is a linear pipeline coordinated by `src/orchestrator.py::HorizonOrchestrator.run()`. Each stage produces a transformed list of `ContentItem` objects:

```
Fetch → URL Dedup → AI Score → Threshold Filter → Topic Dedup → Save → Enrich → Summarize → Deliver
```

- **Fetch**: all scrapers run concurrently via `asyncio.gather` sharing a single `httpx.AsyncClient`.
- **AI Score** (`src/ai/analyzer.py`): sends each item to the LLM, receives `score` (0–10), `reason`, `summary`, `tags`. Retries via `tenacity`.
- **Topic Dedup**: one AI call detects semantically identical stories; drops lower-scored duplicates.
- **Save**: serialises `important_items` to `artifacts/pipeline-output/important_items.json`.
- **Enrich** (`src/ai/enricher.py`): two-step AI pass — identifies concepts, synthesises background from DuckDuckGo search. Stores results in `item.metadata`.
- **Summarize** (`src/ai/summarizer.py`): programmatic Markdown rendering (no LLM call).
- **Deliver**: saves to `data/summaries/`, copies to `docs/_posts/` for GitHub Pages, optionally emails/webhooks.

### Data model

`ContentItem` (Pydantic, `src/models.py`) is the universal unit throughout the pipeline:
- `id`: `"{source}:{subtype}:{native_id}"` — stable identifier
- `ai_score / ai_reason / ai_summary / ai_tags`: set by the analyzer
- `metadata: Dict[str, Any]`: open-ended bag for scraper engagement signals and enricher output

### AI client abstraction

`src/ai/client.py::create_ai_client(config)` is the factory. All providers share `complete(system, user) -> str`:
- **`AnthropicClient`**, **`OpenAIClient`** (covers Ollama, DeepSeek, Alibaba/Qwen, Doubao, MiniMax), **`AzureOpenAIClient`**, **`GeminiClient`**

Token usage is tracked in-memory by `src/ai/tokens.py` and printed after each run.

### Adding a new scraper

1. Create `src/scrapers/your_source.py` extending `BaseScraper`, implement `fetch(since: datetime) -> List[ContentItem]`.
2. Add a config model to `src/models.py` and add the field to `SourcesConfig`.
3. Instantiate and register the scraper in `orchestrator.fetch_all_sources`.

### MCP server

`src/mcp/service.py::HorizonPipelineService` exposes each pipeline stage as an individually-callable method. Stage outputs are persisted as JSON to `data/mcp-runs/<run_id>/`. The FastMCP server in `src/mcp/server.py` wraps these as tools.

### Configuration

`data/config.json` is validated by Pydantic against `src/models.py::Config`. Any string value supports `${ENV_VAR}` interpolation. All API keys are referenced by env-var name, not stored inline. Prompts live in `src/ai/prompts.py` (pipeline) and `src/blog/generator/prompts.py` (blog).

---

## Blog module

`src/blog/` is a self-contained module added on top of upstream Horizon. Intentionally isolated — upstream merges only touch ~5 lines in `src/orchestrator.py` and `src/models.py`.

```
src/blog/
  models.py              ← ScoringDimension, ScoredItem, BlogPost, BlogConfig, PublisherConfig, ImageGenerationConfig
  viewer.py              ← generate_results_html(): self-contained HTML viewer for blog posts
  upload_artifacts.py    ← horizon-upload-artifacts CLI (TrueFoundry ML repo)
  profiles/              ← prompt profiles (news, engineer, ...)
  generator/
    runner.py            ← horizon-blog CLI entry point
    scorer.py            ← multi-dimensional scoring + gate path evaluation
    writer.py            ← BlogWriter: web search + LLM blog post generation
    enricher.py          ← fetch/search-enrich thin-content items before scoring
    fetcher.py           ← async HTTP fetch + DuckDuckGo search fallback
    loader.py            ← load important_items.json, resolve profile list
    reporter.py          ← write ranking_results.md and per-run JSON logs
    prompts.py           ← ITEM_SCORING_* and RELEVANCE_RANKING_* prompt templates
  publisher/
    runner.py            ← horizon-publish CLI entry point
    webflow.py           ← WebflowPublisher (Staged Items API, offset pagination)
    deduplicator.py      ← title-normalised + semantic dedup
    loader.py            ← read Jekyll front matter, convert Markdown → HTML; passes dimensions/inclusion_path through
    converter.py         ← convert_markdown(), reading_time()
    seo.py               ← generate_seo(): one AI call per post for title + meta description
    image_generator.py   ← generate_image_prompt() + generate_image(): LLM prompt → OpenAI gpt-image-2 JPEG bytes
    publisher.py         ← abstract Publisher base class
    category.py          ← assign_category(): one LLM call to pick best-matching Webflow category
```

### Generator flow

`runner.py::_run()` orchestrates:
1. Load `important_items.json` → enrich thin-content items (`enricher.py`)
2. Pre-filter against recently published Webflow posts (semantic dedup, fails open)
3. For each profile: score items (`scorer.py`) or rank by relevance, apply gate paths, select top N
4. Generate blog posts (`writer.py`): web search for context → LLM call → write Markdown
5. Write `posts.json` manifest, update `ranking_results.md` (`reporter.py`), generate HTML viewer (`viewer.py`)

### Publisher flow

`publisher/runner.py::_run()` orchestrates:
1. Load all `posts.json` manifests; dump HTML snapshots to `artifacts/webflow_content/`
2. Fetch recent Webflow items; exact-title dedup (`deduplicator.py`)
3. For each kept post: semantic dedup → generate SEO → assign category → optionally generate cover image → push to Webflow

**Cover image generation** (`image_generator.py`): when `--generate-image` is passed (or `image_generation.enabled: true` in config), the publisher generates an image prompt via LLM (visual concept taxonomy + brand-aware color palettes + randomised art style), then calls OpenAI's `gpt-image-2` through the TrueFoundry gateway. Images are requested as JPEG (`output_format` + `output_compression` in config) to keep article load times reasonable — uncompressed PNG output can be multiple MB per image. Images are saved to `artifacts/cover-images/` and uploaded as Webflow assets. Generation failures are non-fatal — posts publish without an image. The `--dry-run` flag saves images locally without writing to Webflow.

**Draft vs. live**: defaults to draft mode; pass `--publish` to publish live.

### Multi-dimensional scoring and gate paths

Profiles with `scoring_dimensions` use gate-based filtering. `score_items_for_profile()` scores all items concurrently (one LLM call per item), then evaluates gate paths. An item is included if it passes **all** dimensions in **any** gate path (AND within path, OR across paths). First passing path wins — intentional, not an omission. Included items are ranked by a per-path weighted sum; excluded items get `max(weighted_sum across paths)` for reference only.

### Prompt profiles

Each profile is a Python file in `src/blog/profiles/` exporting `PROFILE = BlogPromptProfile(...)`. Add a file + one import in `__init__.py`. Update `docs/blog-profiles.md` when profiles change.

| Profile | Audience | Gate paths |
|---|---|---|
| `news` | General tech readers | Single path: significance + newsworthiness + narrative_clarity |
| `engineer` | ML/MLOps engineers | Path A (research): ml_eng_rel ≥ 7 AND substance ≥ 7; Path B (deployable): ml_eng_rel ≥ 7 AND substance ≥ 5 AND applicability ≥ 6 |

### Blog config (`data/config.json`)

```json
"blog": {
  "generator": {
    "max_posts": 4,
    "profile": "engineer"
  },
  "publisher": {
    "collection_id": "<webflow-news-collection-id>",
    "site_id": "<webflow-site-id>",
    "image_field": "thumbnail-image",
    "authors_collection_id": "<webflow-authors-collection-id>",
    "author_field": "author",
    "categories_collection_id": "<webflow-categories-collection-id>",
    "category_field": "category-2",
    "publish_mode": "draft",
    "max_publish": 4,
    "image_upload_timeout": 120.0,
    "image_generation": {
      "enabled": false,
      "model": "openai-main/gpt-image-2",
      "base_url_env": "TFY_BASE_URL",
      "api_key_env": "TFY_API_KEY",
      "size": "1536x1024",
      "quality": "high",
      "output_format": "jpeg",
      "output_compression": 80
    }
  }
}
```

- `publish_mode`: `"draft"` by default; CLI `--publish` overrides to `"live"`.
- `max_publish`: maximum posts to push per run (overridable via `--max-drafts`).
- `authors_collection_id` / `author_field`: Webflow authors collection used to look up and assign an author to each post.
- `categories_collection_id` / `category_field`: Webflow categories collection used for AI-driven category assignment (`category.py`).
- `image_upload_timeout`: seconds to wait for image upload (default 120).
- `site_id` is required for image upload to Webflow; image generation is skipped with a warning if it is absent.
- `image_generation.enabled: false` means images are only generated when `--generate-image` is passed on the CLI.
- `base_url_env` / `api_key_env` point to env var names for the TrueFoundry gateway credentials.
- Set `"profile": "all"` to run all generator profiles; outputs land in separate subdirectories.

---

## Scripts

### `scripts/run-pipeline.sh` — end-to-end orchestrator

Runs all four stages in sequence with timestamped logging. Designed for cron.

```bash
./scripts/run-pipeline.sh                          # default: 24h window, engineer profile
./scripts/run-pipeline.sh --hours 48 --profile all
./scripts/run-pipeline.sh --max-posts 6
./scripts/run-pipeline.sh --publish live --max-publish 2
./scripts/run-pipeline.sh --dry-run                # skips publish and upload
```

Env: `ARTIFACTS_ML_REPO` — TrueFoundry ML repo name; upload stage is skipped if unset.  
Cron example: `0 8 * * * /path/to/horizon/scripts/run-pipeline.sh >> logs/cron.log 2>&1`

### `scripts/webflow/export_collection.py` — Webflow collection export

Exports a Webflow collection to `artifacts/webflow/<collection>.json`. Useful for inspecting live content or seeding local test fixtures.

```bash
uv run python scripts/webflow/export_collection.py --collection news
uv run python scripts/webflow/export_collection.py --collection authors
uv run python scripts/webflow/export_collection.py --collection categories
uv run python scripts/webflow/export_collection.py --collection news --since-days 30
```

Requires `WEBFLOW_TOKEN` env var. Collection IDs are resolved from `data/config.json`. Handles offset pagination (100 items/page).

### `scripts/webflow/clear_collection.py` — delete every item in a Webflow collection

Deletes all items in a named or arbitrary Webflow collection. Destructive — defaults to a dry-run preview; requires `--execute` (and a typed `yes` confirmation, unless `--yes` is passed) to actually delete.

```bash
uv run python scripts/webflow/clear_collection.py --collection news                  # dry-run
uv run python scripts/webflow/clear_collection.py --collection news --execute        # deletes, asks to confirm
uv run python scripts/webflow/clear_collection.py --collection news --execute --yes  # skip confirmation
uv run python scripts/webflow/clear_collection.py --collection-id 6a3224... --execute --yes  # arbitrary collection ID
```

Requires `WEBFLOW_TOKEN` env var. `--collection {news,authors,categories}` resolves an ID from `data/config.json`; `--collection-id` targets any other collection directly. On a `409 Conflict` (item still referenced by another collection, e.g. a News post referencing an Author), it prints the referencing item and continues rather than aborting. To fully clear a collection with cross-references (e.g. Authors referenced by News), clear the referencing collection (`news`) first.

### `scripts/webflow/publish_payload_collection.py` — create Webflow items from a JSON payload

Creates items in a Webflow collection from a JSON array of `fieldData` objects (e.g. `data/authors_payload.json`), then publishes them live. Defaults to a dry-run preview; requires `--execute` (and a typed `yes` confirmation, unless `--yes` is passed) to actually create.

```bash
uv run python scripts/webflow/publish_payload_collection.py --collection authors --payload data/authors_payload.json                  # dry-run
uv run python scripts/webflow/publish_payload_collection.py --collection authors --payload data/authors_payload.json --execute        # creates + publishes, asks to confirm
uv run python scripts/webflow/publish_payload_collection.py --collection authors --payload data/authors_payload.json --execute --yes  # skip confirmation
uv run python scripts/webflow/publish_payload_collection.py --collection-id 6a3224... --payload path/to/other.json --execute --yes    # arbitrary collection ID
```

Requires `WEBFLOW_TOKEN` env var. `--collection {news,authors,categories}` resolves an ID from `data/config.json`; `--collection-id` targets any other collection directly. Items are created with `isDraft: False`, but Webflow still stages new items as "Queued for publish" until a follow-up `POST .../items/publish` call — the script batches all newly created item IDs into one publish call at the end so they actually go live.

---

## Code style

### Comments
Only add a comment when the **WHY** is non-obvious: a hidden constraint, a subtle invariant, a workaround for a specific bug, or behaviour that would surprise a reader. Never restate what well-named identifiers already say. One short line max — no multi-line blocks.

### Function length
Each function should have a single, nameable responsibility. When a function mixes distinct concerns (data transformation + console output + file I/O), extract each into a private helper and let the original become a readable orchestrator.

### Variable names
Use full, descriptive names. Avoid single-letter variables outside tight throwaway loops (`for i, item in enumerate(...)` is fine; `for si in scored` is not). Avoid cryptic abbreviations (`pdc`, `iid`, `tm`). Timestamp variables should say what they mark (`run_start`, `push_start`) not `t0`/`t1`. Conventional short forms are fine: `e` in `except`, `i`/`j` in index loops, single-letter lambda params in one-liners.