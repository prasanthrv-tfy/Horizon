## 1. Create loader.py

- [x] 1.1 Create `src/blog/loader.py` with `_clean_title`, `load_important_items`, and `resolve_profiles` moved from `runner.py`
- [x] 1.2 Verify imports in `loader.py` are correct (`re`, `json`, `sys`, `pathlib.Path`, `ContentItem`, `PROFILES`)

## 2. Create reporter.py

- [x] 2.1 Create `src/blog/reporter.py` with `_write_ranking_results` and `_write_run_log` moved from `runner.py`
- [x] 2.2 Verify imports in `reporter.py` are correct (`json`, `datetime`, `pathlib.Path`, `ScoredItem`, `BlogPromptProfile`, `BlogPost`)

## 3. Create enricher.py

- [x] 3.1 Create `src/blog/enricher.py` with `_enrich_one` and `enrich_thin_items` moved from `runner.py`
- [x] 3.2 Verify imports in `enricher.py` are correct (`asyncio`, `ContentItem`, `BlogConfig`, `ContentFetcher`, `Console`)

## 4. Create scorer.py

- [x] 4.1 Create `src/blog/scorer.py` with `rank_by_relevance`, `_score_single_item`, `score_items_for_profile`, and `_compute_weighted_sum` moved from `runner.py`
- [x] 4.2 Verify imports in `scorer.py` are correct (AI client, parse_json_response, all scoring models, prompts)

## 5. Slim down runner.py

- [x] 5.1 Replace all extracted functions in `runner.py` with imports from the new modules (`loader`, `enricher`, `scorer`, `reporter`)
- [x] 5.2 Remove all now-unused imports from `runner.py`
- [x] 5.3 Verify `runner.py` retains only `generate_and_save_posts`, `_run`, and `main`

## 6. Verify

- [x] 6.1 Run `uv run python -c "from src.blog.runner import main"` and confirm no import errors
- [x] 6.2 Run `uv run horizon-blog --rank-only --profile news` and confirm identical output to pre-refactor
