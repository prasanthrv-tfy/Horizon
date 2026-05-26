## 1. Generator — Write posts.json manifest

- [x] 1.1 Add `blog_scores: dict[str, float] | None = None` parameter to `generate_and_save_posts()` in `src/blog/generator/runner.py`
- [x] 1.2 After the markdown write loop in `generate_and_save_posts()`, collect manifest entries per post (item_id, title, slug, score, tags, url, published_at, language, profile, filename) and write `artifacts/blog-posts/{profile}/posts.json`
- [x] 1.3 At the gate-path call site (~line 151), build `blog_scores = {si.item.id: si.weighted_sum for si in included[:max_posts]}` and pass it to `generate_and_save_posts`
- [x] 1.4 Remove the Jekyll front-matter write block (lines ~69–94) from `generate_and_save_posts()` — stop writing to `docs/_posts/`

## 2. Publisher — Rewrite loader

- [x] 2.1 Rewrite `src/blog/publisher/loader.py`: replace `load_post(path: Path)` with `load_post(entry: dict, base_dir: Path)` that reads the manifest entry for metadata and the paired `.md` file for markdown content, converts to HTML, and computes reading time

## 3. Publisher — Update deduplicator

- [x] 3.1 Update `src/blog/publisher/deduplicator.py` to accept `list[tuple[dict, Path]]` (entry + base_dir pairs) instead of `list[Path]`; read `entry["title"]` for title comparison instead of parsing filenames

## 4. Publisher — Switch input source

- [x] 4.1 In `src/blog/publisher/runner.py`, replace the `docs/_posts/**/*.md` glob with logic that reads all `artifacts/blog-posts/*/posts.json` manifests and builds a list of `(entry, base_dir)` pairs
- [x] 4.2 Update `_dump_html()` to accept `list[tuple[dict, Path]]` and call the new `load_post(entry, base_dir)` signature
- [x] 4.3 Update the main loop in `_run()` to iterate over `(entry, base_dir)` pairs and call `load_post(entry, base_dir)` and the updated deduplicator

## 5. Verification

- [ ] 5.1 Run `uv run horizon-blog --profile engineer` and confirm `artifacts/blog-posts/engineer/posts.json` exists with decimal `weighted_sum` scores and a `filename` field per entry
- [ ] 5.2 Run `uv run horizon-blog --profile news` and confirm `posts.json` score matches `ai_score` (no regression)
- [ ] 5.3 Confirm no new files are written under `docs/_posts/` after running `horizon-blog`
- [ ] 5.4 Run `uv run horizon-publish` and confirm it reads from `artifacts/blog-posts/`, deduplicates, and pushes drafts correctly
