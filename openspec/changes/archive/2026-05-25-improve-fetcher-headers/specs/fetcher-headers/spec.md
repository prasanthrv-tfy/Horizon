## ADDED Requirements

### Requirement: Browser-like HTTP headers on direct URL fetch
The `ContentFetcher` SHALL initialise its `httpx.AsyncClient` with a Chrome-impersonating header bundle that includes User-Agent, Accept, Accept-Language, Accept-Encoding, Sec-Fetch-Dest, Sec-Fetch-Mode, Sec-Fetch-Site, Sec-Fetch-User, and Upgrade-Insecure-Requests, so that CDN and CMS bot-detection heuristics do not block the request with a 403.

#### Scenario: Headers sent on successful fetch
- **WHEN** `ContentFetcher.fetch_url` issues a GET request
- **THEN** the request MUST include all nine headers from the Chrome 125 bundle defined in `_BROWSER_HEADERS`

#### Scenario: Bot-like User-Agent no longer sent
- **WHEN** `ContentFetcher` is initialised
- **THEN** the User-Agent MUST NOT contain the string `"compatible; Horizon-Blog"`

#### Scenario: Fetch succeeds where it previously returned 403
- **WHEN** a URL is fetched from a site that rejects requests missing `Sec-Fetch-*` or a realistic User-Agent
- **THEN** `fetch_url` SHALL return the article text without raising an exception

#### Scenario: DDG fallback still invoked on genuine failures
- **WHEN** `fetch_url` raises (non-403 error, paywall, or timeout)
- **THEN** the runner SHALL fall back to `search_fallback` as before — no change to fallback logic
