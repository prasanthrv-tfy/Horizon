## ADDED Requirements

### Requirement: AI SEO generation per post
The system SHALL provide a `generate_seo(title: str, markdown: str, ai_client) -> dict` async function in `src/blog/publisher/seo.py` that calls the AI client once per post and returns `{"seo_title": str, "seo_description": str}`.

#### Scenario: Successful SEO generation
- **WHEN** `generate_seo` is called with a valid title and markdown body
- **THEN** it SHALL return a dict with `seo_title` (≤60 chars) and `seo_description` (≤160 chars)

#### Scenario: AI returns oversized values
- **WHEN** the AI response contains a title > 60 chars or description > 160 chars
- **THEN** `generate_seo` SHALL truncate them to the respective limits before returning

### Requirement: SEO generation falls back on AI failure
If the AI call raises an exception, `generate_seo` SHALL return a fallback dict using the original post title truncated to 60 chars as `seo_title` and an empty string as `seo_description`, rather than propagating the exception.

#### Scenario: AI client raises exception
- **WHEN** the AI client raises any exception during SEO generation
- **THEN** `generate_seo` SHALL return `{"seo_title": title[:60], "seo_description": ""}` and log a warning
