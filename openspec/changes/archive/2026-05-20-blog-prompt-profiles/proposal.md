## Why

The current blog generation uses a single hardcoded prompt that produces journalist-style content ("technology journalist and technical writer") focused on business impact and enterprise strategy. This is the wrong tone for AI/ML engineers and MLOps practitioners — the primary audience for TrueFoundry. Switching prompts today requires editing Python source. There is no way to compare styles or iterate without code changes.

## What Changes

- **New** `src/blog/profiles/` subpackage with one Python file per prompt profile
- **New** `src/blog/profiles/profile.py` — `BlogPromptProfile` dataclass bundling all prompts for a profile (`blog_system`, `blog_user`, `research_system`, `research_user`)
- **New** `src/blog/profiles/journalist.py` — current prompts extracted verbatim into a named profile
- **New** `src/blog/profiles/practitioner.py` — new ML-engineer-focused prompts: practitioner persona, engineering-oriented structure, technical-depth research queries
- **New** `src/blog/profiles/__init__.py` — `PROFILES` registry dict mapping name → profile
- **Modified** `src/blog/models.py` — `BlogConfig` gains `prompt_profile: str = "journalist"`, `audience_context: str = ""`, `platform_context: str = ""`
- **Modified** `src/blog/writer.py` — `BlogWriter` accepts a `BlogPromptProfile`; uses its `blog_system`/`blog_user` for generation and `research_system`/`research_user` for concept/query extraction instead of the shared `CONCEPT_EXTRACTION_*` prompts
- **Modified** `src/blog/runner.py` — resolves profile(s) from config; if `prompt_profile == "all"`, iterates all registered profiles; output goes to `{output_dir}/{profile_name}/`
- **Modified** `src/blog/prompts.py` — `BLOG_POST_SYSTEM` and `BLOG_POST_USER` removed (now live in `journalist.py`); `RELEVANCE_RANKING_*` stays as shared

## Capabilities

### New Capabilities

- `blog-prompt-profiles`: Runtime-selectable prompt profiles for blog generation, with per-profile output directories enabling side-by-side comparison

### Modified Capabilities

- `blog-generation`: Now profile-aware — output directory is `{output_dir}/{profile_name}/`; `BlogWriter` uses profile prompts end-to-end including web research query generation

## Impact

- `src/blog/profiles/` — new subpackage (4 new files)
- `src/blog/models.py` — 3 fields added to `BlogConfig`
- `src/blog/writer.py` — constructor and prompt usage updated; no change to web search, retry, or output logic
- `src/blog/runner.py` — profile resolution + "all" sentinel handling added
- `src/blog/prompts.py` — `BLOG_POST_SYSTEM` and `BLOG_POST_USER` removed; `RELEVANCE_RANKING_*` untouched
- `data/config.json` — optional new fields under `blog` section
- No changes to upstream files, scrapers, enricher, or delivery
