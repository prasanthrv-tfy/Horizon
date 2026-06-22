## Why

Blog posts published to Webflow currently have no featured image, making them visually plain in the CMS and on the site. Adding AI-generated cover images at publish time improves presentation without cluttering the generation step with images that may never be used.

## What Changes

- **New**: AI-generated cover image per post using Stability AI (via TrueFoundry gateway) during the publish step
- **New**: Webflow asset upload — generated image is uploaded to Webflow's asset library and referenced in the CMS item's `cover-image` field
- **New**: `--generate-image` CLI flag on `horizon-publish` to opt in to image generation at runtime
- **New**: `--publish` CLI flag on `horizon-publish` to publish items live immediately (default remains draft)
- **New**: `ImageGenerationConfig` model nested in `PublisherConfig` for image model/API configuration
- **New**: `site_id` and `image_field` fields added to `PublisherConfig` (needed for Webflow Assets API)

## Capabilities

### New Capabilities

- `cover-image-generation`: Generate an AI cover image for a blog post using Stability AI via TrueFoundry gateway; includes LLM-assisted prompt construction and Webflow asset upload
- `publisher-publish-mode`: CLI toggle between draft and live-publish when pushing posts to Webflow

### Modified Capabilities

<!-- No existing spec-level requirements are changing -->

## Impact

- **`src/blog/publisher/`** — new files `image_generator.py`; changes to `runner.py`, `webflow.py`
- **`src/blog/models.py`** — new `ImageGenerationConfig` model; `PublisherConfig` gains `site_id`, `image_field`, `image_generation` fields
- **`data/config.json`** — new `site_id`, `image_field`, and `image_generation` keys under `blog.publisher`
- **Dependencies**: `openai` package (already installed) used for Stability API calls via TrueFoundry gateway
- **Environment**: `TFY_BASE_URL` and `TFY_API_KEY` env vars (already used by the pipeline)
- **Webflow**: requires `assets:write` scope on the Webflow API token; collection must have a `cover-image` image field
