## Context

`ContentFetcher.__aenter__` initialises an `httpx.AsyncClient` with a single header:

```python
headers={"User-Agent": "Mozilla/5.0 (compatible; Horizon-Blog/1.0)"}
```

The `"compatible; Bot/1.0"` pattern is a well-known bot signal. On top of that, the absence of `Accept`, `Accept-Language`, `Accept-Encoding`, and the Chrome-specific `Sec-Fetch-*` family causes CDNs and CMS platforms to respond with 403. The fetch fails, the runner falls back to DuckDuckGo search, and content quality degrades.

## Goals / Non-Goals

**Goals:**
- Replace the header dict with a realistic Chrome 125 / macOS bundle that passes basic bot-detection heuristics.
- Keep the change contained to one constant in `fetcher.py`.

**Non-Goals:**
- TLS/JA3 fingerprint spoofing (sites using deep TLS inspection are a tiny minority of news sources; `curl_cffi` would be needed and is not worth the dependency).
- Cookie or session management.
- Rotating user agents.
- Handling paywalled content (NYT, WSJ) — the DDG fallback remains correct for those.

## Decisions

**Stay on `httpx`, don't switch to `urllib`**

Both libraries send whatever headers you provide. `urllib` is synchronous, which would require `asyncio.run_in_executor` wrapping in an async context — adding noise for zero benefit. httpx already handles async, redirects, and compression.

**Use a single fixed Chrome UA rather than a rotating pool**

A convincing static UA is sufficient for CDN-level bot detection. Rotation adds complexity (state, list maintenance) with marginal gain for a pre-scoring enrichment step where best-effort is acceptable.

**Header bundle to use** (Chrome 125, macOS):

```python
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}
```

These are the exact headers Chrome sends on a top-level navigation with no referrer — the most natural pattern for reading an article URL directly.

## Risks / Trade-offs

- **Sites with advanced bot detection** (Cloudflare JS challenge, Datadome) → Still blocked. DDG fallback handles these correctly already; no regression.
- **Header staleness** — Chrome UA strings age slowly. The bundle requires no maintenance for 12–18 months. → Accept; update when clearly stale.
- **httpx decompresses `br` (Brotli) automatically** as of httpx 0.20+. Advertising `br` in `Accept-Encoding` is safe as long as the installed httpx version supports it (Horizon already depends on a recent httpx). → No action needed.
