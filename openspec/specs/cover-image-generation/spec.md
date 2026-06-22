## ADDED Requirements

### Requirement: Generate AI cover image during publish
The publisher SHALL generate an AI cover image for each blog post when image generation is enabled (via config or `--generate-image` CLI flag). Generation MUST occur after SEO metadata is available and before the Webflow CMS item is created.

#### Scenario: Image generation enabled and succeeds
- **WHEN** `--generate-image` flag is set or `image_generation.enabled` is `true` in config
- **THEN** the publisher generates one cover image per post and attaches it to the Webflow CMS item's `cover-image` field

#### Scenario: Image generation disabled
- **WHEN** neither `--generate-image` flag nor `image_generation.enabled` is set
- **THEN** the publisher publishes the post without a cover image (existing behavior)

### Requirement: LLM-assisted image prompt construction
The system SHALL use the existing `ai_client` to generate a Stability-optimised visual prompt from the post's title, tags, and SEO description before calling the image model.

#### Scenario: Prompt generation succeeds
- **WHEN** title, tags, and SEO description are available
- **THEN** the system produces a vivid, photorealistic scene description suitable for Stability AI, with no instructions to include text or words in the image

#### Scenario: Prompt generation fails
- **WHEN** the LLM call for prompt generation fails
- **THEN** the system falls back to a template prompt (`"Professional tech blog featured image about: {title}"`) and continues

### Requirement: Image generation via Stability AI (TrueFoundry gateway)
The system SHALL call `image-gen/stability.stable-image-core-v1-1` via the TrueFoundry OpenAI-compatible gateway using `response_format="b64_json"` and decode the result to bytes.

#### Scenario: Image generation succeeds
- **WHEN** the Stability API call returns a valid `b64_json` response
- **THEN** the system decodes the base64 payload to raw PNG bytes

#### Scenario: Image generation fails
- **WHEN** the Stability API call raises an exception
- **THEN** the system logs a warning, skips image attachment, and continues publishing the post

### Requirement: Upload image as Webflow asset
The system SHALL upload generated image bytes to Webflow's Assets API using the two-step presigned S3 flow and reference the asset in the CMS item.

#### Scenario: Asset upload succeeds
- **WHEN** image bytes are available and `site_id` is configured
- **THEN** the system POST to `/v2/sites/{site_id}/assets` with filename and MD5 hash, receives upload credentials, POST multipart bytes to the presigned S3 URL, and attaches the returned `asset_id` and `hostedUrl` to the CMS item's `cover-image` field

#### Scenario: Asset upload fails
- **WHEN** the Webflow Assets API call or S3 upload fails
- **THEN** the system logs a warning, skips image attachment, and continues publishing the post without an image

#### Scenario: `site_id` not configured
- **WHEN** `image_generation` is enabled but `publisher.site_id` is empty
- **THEN** the system logs a warning and skips image generation entirely

### Requirement: Image generation configuration
The system SHALL read image generation settings from `config.blog.publisher.image_generation` with the following fields: `enabled` (bool, default false), `model` (str), `base_url_env` (str), `api_key_env` (str), `size` (str).

#### Scenario: Default config disables image generation
- **WHEN** no `image_generation` block is present in config
- **THEN** image generation is disabled by default (no images generated, no API calls made)
