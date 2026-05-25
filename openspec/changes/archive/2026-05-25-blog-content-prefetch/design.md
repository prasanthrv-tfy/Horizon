## Context

`_score_single_item` in `src/blog/runner.py` builds its item text from `item.content[:400]`. For most RSS-sourced items, `item.content` is the feed's `summary` or `description` field — typically 100–200 characters. For HackerNews items, it includes the full article text and comment thread (sometimes 25k+ chars). The result is inconsistent scoring signal: HN items score accurately; blog/announcement items score on title rephrasing.

The fix is a pre-scoring enrichment step in the blog module that brings RSS-thin items up to a usable content length before scoring runs.

## Goals / Non-Goals

**Goals:**
- Items with thin content (< 500 chars) get their full article text before scoring.
- Fetch failures (blocked, timeout, 403, network error) fall back gracefully to a search-based enrichment.
- Enrichment is in-memory: `important_items.json` is never modified.
- No changes to any upstream Horizon file.

**Non-Goals:**
- Persisting enriched content to disk or back to `important_items.json`.
- Enriching items that already have sufficient content (>= 500 chars).
- Replacing the BlogWriter's existing web research step (which runs later, per included item).
- Full article extraction quality (newspaper3k, readability) — simple HTML stripping is sufficient for scoring signal.

## Decisions

### 1. Thin content threshold: 500 chars

Items with >= 500 chars already have enough signal for the scorer. In the 2026-05-25 run, the median item had ~165 chars and the richest RSS item had ~1900 chars. 500 is a clean break between "RSS excerpt" and "has real content".

**Alternative considered**: Always fetch all items. Rejected — adds latency for ~10 items that already have good content (Gradient-based Planning has 25k chars from HN), and increases the chance of rate-limiting.

### 2. Fetch strategy: httpx async GET, HTML stripped to plain text

Use `httpx.AsyncClient` (already a project dependency) with a 10-second timeout. Strip HTML tags using stdlib `html.parser` (no new dependency). Take the first 2000 chars of the stripped text.

**Why 2000 chars?** The scorer's content preview is widened to 1500 chars. 2000 gives a small buffer so that stripping artifacts and navigation text at the start of a page don't use up the entire window.

**Alternative considered**: `newspaper3k` or `readability-lxml` for cleaner extraction. Rejected — adds dependencies and complexity; simple HTML stripping is sufficient to give the scorer article text vs. navigation junk.

### 3. Fallback strategy: DuckDuckGo search

If the fetch fails (any exception, timeout, non-200 status, or returned text < 200 chars after stripping), run a DuckDuckGo search with the query `"{title}" {top_2_tags}`. Concatenate the top 3 result snippets (title + body). This uses the same `duckduckgo_search` library already used by `BlogWriter`.

**Why search as fallback rather than skip?** For items like GPT-Rosalind, the URL is fetchable but thin by design (OpenAI landing pages). Search results for "Introducing GPT-Rosalind OpenAI life sciences" will return snippets from third-party coverage that contain the architecture details and benchmark numbers the page itself omits. This adds signal even when the source page is sparse.

**Why not search-first?** Direct fetch is more authoritative and faster (one HTTP call vs. multiple search + result calls). Search as primary would also add latency to all thin items, not just those where fetch fails.

### 4. Content preview in `_score_single_item`: widened from 400 to 1500 chars

The existing 400-char cap means enriched content is still truncated before the scorer sees it. 1500 chars captures a meaningful article introduction and is well within LLM context limits. The scorer prompt already handles varying content lengths.

### 5. Concurrency: shared semaphore, limit 5

Fetch and search calls run concurrently with a semaphore of 5, matching the existing `analysis_concurrency` pattern in the runner. Reduces total enrichment time from O(N×fetch_time) to O(N/5×fetch_time).

### 6. Logging

Console output per enriched item:
- `✓ fetched {url[:60]}` on successful URL fetch
- `⚠ fetch failed ({reason}), using search for: {title[:50]}` on fallback to search
- `✗ enrichment failed for: {title[:50]}` if both strategies fail (scoring proceeds with original thin content)

## Risks / Trade-offs

- **Fetch latency**: Enriching 30–40 thin items at concurrency=5 adds ~10–20 seconds before scoring. Acceptable for a batch job.
- **Blocked URLs**: Major AI company blog pages (OpenAI, Anthropic, Google) may return 403 or bot-detection responses. The search fallback handles this.
- **HTML stripping quality**: Navigation bars, cookie banners, and footers may appear in the extracted text and consume the 2000-char window. This is acceptable — even partial article text is better than a 160-char RSS excerpt.
- **Search quality variance**: DuckDuckGo results for very new announcements may not yet be indexed. In this case the enrichment adds little and the scorer falls back to the original content. No regression.

## Open Questions

- Should the thin content threshold be configurable in `BlogConfig`? Starting with a hard-coded 500 — add config key if needed after observing runs.
- Should enriched content be logged to `data/blog-runs/` for inspection? Not in v1 — the run log already captures dimension scores with reasons, which reveals whether enrichment helped.