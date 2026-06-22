## 1. Config & Models

- [x] 1.1 Add `ImageGenerationConfig` Pydantic model to `src/blog/models.py` with fields: `enabled`, `model`, `base_url_env`, `api_key_env`, `size`
- [x] 1.2 Extend `PublisherConfig` in `src/blog/models.py` with `site_id: str = ""`, `image_field: str = ""`, and `image_generation: ImageGenerationConfig = ImageGenerationConfig()`
- [x] 1.3 Update `data/config.json` to add `site_id`, `image_field: "cover-image"`, and `image_generation` block under `blog.publisher`

## 2. Image Generator

- [x] 2.1 Create `src/blog/publisher/image_generator.py` with `generate_image_prompt(title, tags, seo_description, ai_client) -> str` — LLM call that returns a Stability-optimised visual prompt; falls back to template on failure
- [x] 2.2 Add `generate_image(prompt, config: ImageGenerationConfig) -> bytes | None` to `image_generator.py` — instantiates `AsyncOpenAI` with TrueFoundry base URL and headers, calls `images.generate` with `response_format="b64_json"`, decodes and returns bytes; returns `None` on failure

## 3. Webflow Asset Upload

- [x] 3.1 Add `upload_asset(self, image_bytes: bytes, filename: str, site_id: str) -> dict | None` to `WebflowPublisher` in `src/blog/publisher/webflow.py` — step 1: POST to `/v2/sites/{site_id}/assets` with filename + MD5 hash; step 2: POST multipart to presigned S3 URL; returns `{"id": ..., "hostedUrl": ...}` or `None` on failure
- [x] 3.2 Extend `add_draft(self, item: dict, is_draft: bool = True)` in `webflow.py` to accept `is_draft` parameter (replaces hardcoded `True`) and to include `cover-image` field in `fieldData` when `item.get("image_asset")` is set and `self._image_field` is configured
- [x] 3.3 Update `WebflowPublisher.__init__` to accept and store `image_field: str = ""` parameter

## 4. Publisher Runner Integration

- [x] 4.1 Add `--publish` argparse flag to `main()` in `src/blog/publisher/runner.py`; pass `publish` bool to `_run()`
- [x] 4.2 Add `--generate-image` argparse flag to `main()` in `runner.py`; pass `generate_image` bool to `_run()`
- [x] 4.3 In `_run()`, instantiate `WebflowPublisher` with `image_field` from config; pass `is_draft=not publish` when calling `add_draft()`
- [x] 4.4 In `_publish_batch()`, after SEO generation: if image generation is active (`config.image_generation.enabled or generate_image_flag`) and `site_id` is set, call `generate_image_prompt` → `generate_image` → `publisher.upload_asset`; set `post["image_asset"]` on success; wrap entire block in try/except that logs and continues on failure

## 5. Verification

- [x] 5.1 Run `uv run horizon-publish` (no flags) — confirm existing behavior unchanged: posts pushed as drafts, no image field
- [ ] 5.2 Run `uv run horizon-publish --generate-image` — confirm image generation runs, Webflow draft has `cover-image` populated
- [ ] 5.3 Run `uv run horizon-publish --publish` — confirm `isDraft: false` in Webflow
- [ ] 5.4 Test failure path: set invalid model name in config, run with `--generate-image` — confirm publish succeeds with warning logged and no image attached
