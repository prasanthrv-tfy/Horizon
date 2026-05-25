## 1. Create `src/blog/fetcher.py`

- [x] 1.1 Add `fetch_url(url: str, timeout: int = 10) -> str` — async HTTP GET via `httpx.AsyncClient`, strip HTML tags using stdlib `html.parser`, return first 2000 chars of plain text; raise on non-200 or exception
- [x] 1.2 Add `search_fallback(title: str, tags: list[str]) -> str` — build query `"{title}" {" ".join(tags[:2])}`, run DuckDuckGo search (same library as `BlogWriter`), concatenate top 3 result snippets (title + body), return result string
- [x] 1.3 Add `ContentFetcher` class wrapping both methods with a shared `httpx.AsyncClient` (created once, closed after enrichment batch)

## 2. Add `enrich_thin_items()` to `src/blog/runner.py`

- [x] 2.1 Add `THIN_CONTENT_THRESHOLD = 500` constant
- [x] 2.2 Implement `async def enrich_thin_items(items: List[ContentItem], console: Console) -> None` — filters to items where `len(item.content or "") < THIN_CONTENT_THRESHOLD`, runs fetch+fallback concurrently (semaphore=5), writes enriched text back to `item.content` in-memory
- [x] 2.3 Log per-item outcome: `✓ fetched`, `⚠ fetch failed → search`, `✗ enrichment failed`
- [x] 2.4 Call `await enrich_thin_items(items, console)` in `_run()` before the `for profile in profiles:` loop (enrichment runs once, shared across all profiles)

## 3. Widen content preview in `_score_single_item`

- [x] 3.1 Change `item.content.split("--- Top Comments ---")[0].strip()[:400]` to `[:1500]` in `_score_single_item`

## 4. Update the blog-content-prefetch spec

- [x] 4.1 Write `openspec/specs/blog-content-prefetch/spec.md` with requirements and scenarios covering: thin item detection, fetch success path, search fallback path, dual failure path, in-memory-only constraint, no change to items with >= 500 chars content

## 5. Verify

- [x] 5.1 Run `uv run horizon-blog --rank-only` and confirm GPT-Rosalind shows a fetched/searched content log line and its `technical_substance` score changes from 4
- [x] 5.2 Confirm `important_items.json` is unmodified after the run (enrichment is in-memory only)
- [x] 5.3 Confirm items already above 500 chars (e.g., Gradient-based Planning) show no enrichment log line and score identically