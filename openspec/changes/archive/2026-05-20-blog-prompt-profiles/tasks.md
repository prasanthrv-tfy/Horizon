## 1. Create src/blog/profiles/ subpackage

- [x] 1.1 Create `src/blog/profiles/profile.py` with `BlogPromptProfile` dataclass (`name`, `blog_system`, `blog_user`, `research_system`, `research_user` fields)
- [x] 1.2 Create `src/blog/profiles/journalist.py` — move `BLOG_POST_SYSTEM` and `BLOG_POST_USER` from `src/blog/prompts.py` here, add `research_system`/`research_user` using current `CONCEPT_EXTRACTION_SYSTEM/USER` text, export as `PROFILE = BlogPromptProfile(name="journalist", ...)`
- [x] 1.3 Create `src/blog/profiles/practitioner.py` — write new ML-engineer-focused `blog_system`, `blog_user`, `research_system`, `research_user` prompts, export as `PROFILE = BlogPromptProfile(name="practitioner", ...)`
- [x] 1.4 Create `src/blog/profiles/__init__.py` — import both profiles, build `PROFILES = {p.name: p for p in [journalist.PROFILE, practitioner.PROFILE]}`

## 2. Update BlogConfig

- [x] 2.1 Add `prompt_profile: str = "journalist"`, `audience_context: str = ""`, `platform_context: str = ""` to `BlogConfig` in `src/blog/models.py`

## 3. Update BlogWriter

- [x] 3.1 Change `BlogWriter.__init__` to accept `profile: BlogPromptProfile` instead of importing prompts at module level
- [x] 3.2 In `_generate_single_post`: replace `BLOG_POST_SYSTEM/USER` references with `self.profile.blog_system/blog_user`; inject `audience_context`, `platform_context`, `language_name` into `blog_system` using a safe format call
- [x] 3.3 In `_extract_concepts`: replace `CONCEPT_EXTRACTION_SYSTEM/USER` with `self.profile.research_system/research_user`
- [x] 3.4 Remove `BLOG_POST_SYSTEM`, `BLOG_POST_USER`, `CONCEPT_EXTRACTION_SYSTEM`, `CONCEPT_EXTRACTION_USER` imports from `src/blog/writer.py`

## 4. Update runner.py

- [x] 4.1 Add `resolve_profiles(config: BlogConfig) -> list[BlogPromptProfile]` helper — returns `list(PROFILES.values())` if `prompt_profile == "all"`, else `[PROFILES[prompt_profile]]` (raise clear error if name not found)
- [x] 4.2 Update `generate_and_save_posts` to accept a `profile` argument and pass it to `BlogWriter`; write output to `{output_dir}/{profile.name}/` and Jekyll posts to `docs/_posts/{profile.name}/`
- [x] 4.3 Update `_run()` to call `resolve_profiles`, loop over profiles, call `generate_and_save_posts` for each

## 5. Clean up src/blog/prompts.py

- [x] 5.1 Remove `BLOG_POST_SYSTEM` and `BLOG_POST_USER` from `src/blog/prompts.py` (now live in `journalist.py`)
- [x] 5.2 Verify `RELEVANCE_RANKING_SYSTEM` and `RELEVANCE_RANKING_USER` remain untouched

## 6. Write the practitioner prompts (content work)

- [x] 6.1 `practitioner.py` blog_system: persona is "senior ML engineer writing for peers"; structure is TL;DR → What technically changed → How it works → What this means for practitioners → How to try it → Caveats; explicitly tell the model the audience knows PyTorch/Kubernetes/LLMs and to skip background explanations
- [x] 6.2 `practitioner.py` blog_user: same variables as journalist (`{title}`, `{url}`, `{content}`, etc.) plus `{audience_context}` and `{platform_context}` placeholders
- [x] 6.3 `practitioner.py` research_system: instruct the model to identify technical papers, benchmarks, implementations, and API/SDK references to research — NOT concepts needing explanation
- [x] 6.4 `practitioner.py` research_user: mirror structure of existing `CONCEPT_EXTRACTION_USER` but asking for "technical depth queries" instead of "concept explanation queries"

## 7. Verify

- [x] 7.1 `uv run python -c "from src.blog.profiles import PROFILES; print(list(PROFILES))"` prints `['journalist', 'practitioner']`
- [x] 7.2 Run `uv run horizon-blog` with `prompt_profile: "journalist"` — posts appear in `data/blog-posts/journalist/`
- [x] 7.3 Run `uv run horizon-blog` with `prompt_profile: "practitioner"` — posts appear in `data/blog-posts/practitioner/`
- [x] 7.4 Run `uv run horizon-blog` with `prompt_profile: "all"` — posts appear in both subdirectories
- [x] 7.5 Confirm invalid profile name raises a clear error message
