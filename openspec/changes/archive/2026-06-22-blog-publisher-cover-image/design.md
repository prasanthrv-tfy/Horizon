## Context

The Horizon blog publisher (`src/blog/publisher/`) runs as a separate step after post generation. It reads `posts.json` manifests, deduplicates, generates SEO metadata via one LLM call per post, then pushes to Webflow CMS. Currently all posts are pushed as drafts (`isDraft: true`) and no featured image is attached.

The pipeline uses a TrueFoundry-hosted LLM gateway for all AI calls. The same gateway exposes Stability AI image models (`image-gen/stability.stable-image-core-v1-1`) through an OpenAI-compatible `images.generate` endpoint. The `openai` package is already installed.

Webflow's Assets API uses a presigned S3 upload flow: POST to Webflow to get an upload URL → POST multipart bytes to that URL → reference the returned asset ID in the CMS item. No external S3 account is required.

## Goals / Non-Goals

**Goals:**
- Generate one AI cover image per post at publish time, upload it to Webflow assets, and attach it to the CMS item
- Add `--generate-image` CLI flag to opt in at runtime (config default: off)
- Add `--publish` CLI flag to switch from draft to live immediately
- Fail gracefully — if image generation or upload fails, publish continues without image

**Non-Goals:**
- Storing generated images locally or in non-Webflow storage
- Image generation during the blog generation step (`horizon-blog`)
- Changing the core Horizon pipeline (`src/orchestrator.py`, `src/ai/`)
- Supporting image generation providers other than the TrueFoundry gateway

## Decisions

### D1: Two-step image generation (LLM prompt → Stability)

**Decision**: Use a fast LLM call to convert post title + tags + SEO description into a Stability-optimised visual prompt, then feed that to the image model.

**Rationale**: Stability AI responds poorly to raw article titles — it needs vivid, photorealistic scene descriptions. A short LLM call (same `ai_client` already in scope) produces prompts like "A glowing neural network graph over a dark server room, cinematic lighting" instead of "New LLM benchmark released". Quality improvement for ~$0.001 extra per post.

**Alternative considered**: Template-based prompt (`f"Professional tech blog image about: {title}"`). Simpler but significantly lower image quality — rejected.

### D2: Separate OpenAI client for image generation

**Decision**: Instantiate a dedicated `AsyncOpenAI` client in `image_generator.py` for the Stability image API call, separate from the main `ai_client`.

**Rationale**: The existing `ai_client` abstraction (`src/ai/client.py`) only exposes `complete(system, user) -> str` and has no image generation method. Extending it would touch core Horizon code (explicitly out of scope). The `AsyncOpenAI` client is already available via the installed `openai` package and the TrueFoundry gateway accepts OpenAI-compatible requests.

**Alternative considered**: Extend `AnthropicClient`/`OpenAIClient` with an `generate_image()` method. Cleaner long-term but requires modifying core files — rejected for this change.

### D3: Asset upload method on WebflowPublisher

**Decision**: Add `upload_asset(image_bytes, filename, site_id)` as a method on the existing `WebflowPublisher` class rather than a standalone function.

**Rationale**: `WebflowPublisher` already holds an `httpx.AsyncClient` with the correct `Authorization: Bearer` header. Reusing it avoids duplicating auth setup. The Webflow Assets API is a natural extension of the same client.

### D4: `--generate-image` overrides config; config default is `enabled: false`

**Decision**: Image generation activates when `config.blog.publisher.image_generation.enabled = true` OR `--generate-image` CLI flag is set.

**Rationale**: Keeps the default safe (no surprise image costs), lets the config enable it permanently for automated runs, and lets the CLI opt in for one-off runs.

### D5: `--publish` flag with draft as default

**Decision**: Add `is_draft: bool = True` parameter to `add_draft()`. CLI `--publish` sets `is_draft=False`.

**Rationale**: Minimal change — one parameter, one payload key. Default draft behavior is preserved, no existing callers break.

## Risks / Trade-offs

- **Image generation latency** (~5–10s per post via Stability) → Runs after SEO, adds ~10s per post. Acceptable for a manual publish step; could be parallelised with SEO in a future change.
- **Stability model quality variance** → Image quality varies with prompt. The LLM-assisted prompt step (D1) mitigates most of this, but some posts will produce less relevant images. Operator can review in Webflow before publishing.
- **Webflow `assets:write` scope** → The existing Webflow API token may not have this scope. Fails open (publish continues without image, warning logged). Operator needs to add the scope manually.
- **4MB image size limit** → Stability's `1024x1024` PNG output is typically 1–3MB. Should be within Webflow's limit, but worth monitoring.
- **`site_id` config requirement** → Asset upload requires `site_id`, which is not currently in `PublisherConfig`. If missing when image generation is enabled, the upload step is skipped with a warning.

## Open Questions

- None — all decisions are resolved. `site_id` and `image_field` (`cover-image`) are known from the user's Webflow setup.
