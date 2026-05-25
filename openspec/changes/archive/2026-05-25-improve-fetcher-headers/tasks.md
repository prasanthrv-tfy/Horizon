## 1. Update ContentFetcher headers

- [x] 1.1 Define `_BROWSER_HEADERS` module-level constant in `src/blog/fetcher.py` with the full Chrome 125 / macOS header bundle (User-Agent, Accept, Accept-Language, Accept-Encoding, Sec-Fetch-Dest, Sec-Fetch-Mode, Sec-Fetch-Site, Sec-Fetch-User, Upgrade-Insecure-Requests)
- [x] 1.2 Replace the inline `headers={"User-Agent": ...}` dict in `ContentFetcher.__aenter__` with `headers=_BROWSER_HEADERS`

## 2. Verify

- [x] 2.1 Run `uv run horizon-blog` against at least one item whose URL previously returned 403 and confirm the direct fetch now succeeds (check run log in `data/blog-runs/`)
