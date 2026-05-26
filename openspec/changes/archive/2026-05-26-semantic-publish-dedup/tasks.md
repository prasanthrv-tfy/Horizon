## 1. Semantic dedup function

- [x] 1.1 Add prompt constants (`_SEMANTIC_DEDUP_SYSTEM`, `_SEMANTIC_DEDUP_USER`) to `deduplicator.py`
- [x] 1.2 Add `async def semantic_is_duplicate(title, existing_titles, ai_client) -> tuple[bool, str | None]` to `deduplicator.py` — calls LLM, parses JSON response, fails open on error

## 2. Publisher loop integration

- [x] 2.1 Update publish loop in `runner.py` to call `semantic_is_duplicate` per candidate before `add_draft`; collect semantic skips separately from title skips
- [x] 2.2 Update end-of-run summary in `runner.py` to report title-match and semantic-match skips with distinct labels
