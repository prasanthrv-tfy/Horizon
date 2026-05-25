## Why

The `ContentFetcher` in `src/blog/fetcher.py` uses a bot-identifying User-Agent and omits the Accept/Sec-Fetch headers that real browsers always send, causing many news sites and CDNs (Cloudflare, Akamai) to return 403s and fall through to the less-reliable DuckDuckGo search fallback. Adding a realistic Chrome-like header bundle will let the direct URL fetch succeed for the majority of sources.

## What Changes

- Replace the single `User-Agent` header on `httpx.AsyncClient` with a full browser-impersonating header bundle (User-Agent, Accept, Accept-Language, Accept-Encoding, Sec-Fetch-Dest, Sec-Fetch-Mode, Sec-Fetch-Site, Sec-Fetch-User, Upgrade-Insecure-Requests).
- No library change — stays on `httpx.AsyncClient`.
- No change to the fetch/fallback control flow in `runner.py`.

## Capabilities

### New Capabilities
- `fetcher-headers`: Browser-like HTTP headers for the ContentFetcher to reduce 403 errors on direct URL fetches.

### Modified Capabilities

## Impact

- `src/blog/fetcher.py` — only file changed.
- No new dependencies.
- Higher direct-fetch success rate; DDG fallback invoked less often.
