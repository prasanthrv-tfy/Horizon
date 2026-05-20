## Context

`src/blog/` was introduced to isolate blog generation from upstream Horizon. Currently `BlogWriter` imports `BLOG_POST_SYSTEM/USER` from `src/blog/prompts.py` and `CONCEPT_EXTRACTION_*` from `src/ai/prompts.py` directly. There is no abstraction between "which prompt style" and "how blog generation runs". Adding a second style means duplicating `BlogWriter` or scattering conditionals through it.

The fix is a thin profile layer: a `BlogPromptProfile` dataclass that `BlogWriter` accepts, decoupling prompt selection from generation logic entirely.

## Goals / Non-Goals

**Goals:**
- Profile selection is a single config field (`prompt_profile`)
- Adding a new profile = adding one Python file, no other changes
- "all" runs every profile in one invocation, outputs to separate subdirectories
- `audience_context` and `platform_context` are runtime-injectable without touching profile files
- Practitioner profile uses different web research queries (not "what is X?" but "what technical depth?")

**Non-Goals:**
- External/file-based profile loading (profiles live in code, not `data/`)
- Ranking profile variants (ranking stays shared for now)
- Per-language profile selection

## Decisions

### 1. `BlogPromptProfile` as a plain dataclass, not a Pydantic model

**Decision:** `@dataclass` in `src/blog/profiles/profile.py`.

**Why:** Profiles are code-defined constants, not user-supplied data. They don't need validation, serialization, or env-var interpolation. A dataclass keeps them lightweight and avoids circular imports with `src/blog/models.py` (which is Pydantic and imported by config loading).

---

### 2. One Python file per profile

**Decision:** `src/blog/profiles/journalist.py` and `src/blog/profiles/practitioner.py`, each exporting `PROFILE = BlogPromptProfile(...)`.

**Why:** Python triple-quoted strings are the most ergonomic format for multi-paragraph prompts. Syntax highlighting works, diffs are clean, git history tracks prompt evolution. No parsing, no file I/O at startup. Adding a profile is just adding a file and one import in `__init__.py`.

**Alternative considered:** YAML files under `data/prompts/`. Rejected — YAML multi-line strings are awkward, requires file loading logic, and moves prompts outside the module boundary (harder to discover).

---

### 3. Profile carries its own research prompts

**Decision:** `BlogPromptProfile` includes `research_system: str` and `research_user: str`. `BlogWriter._extract_concepts` uses these instead of the shared `CONCEPT_EXTRACTION_*` from `src/ai/prompts.py`.

**Why:** The web search step is the biggest quality lever after the blog system prompt. The journalist profile searches for "concepts needing explanation" (producing "what is npm?" queries). The practitioner profile should search for "technical depth and implementations" (producing "OfficeQA Pro benchmark paper", "vLLM on-prem architecture" queries). Bundling this in the profile keeps the change self-contained.

**Impact on upstream:** `src/ai/prompts.py::CONCEPT_EXTRACTION_*` is still used by the enricher — no change there. `BlogWriter` just stops importing it.

---

### 4. Context injection via format variables in profile templates

**Decision:** Profile `blog_system` strings use `{audience_context}` and `{platform_context}` as optional placeholders. `BlogWriter` calls `.format(audience_context=..., platform_context=..., language_name=...)` before passing to the AI client.

**Why:** Audience and platform context are deployment-specific (different teams, different TrueFoundry descriptions). Keeping them in `BlogConfig` rather than hardcoded in profile files means profiles are reusable across deployments. If a profile doesn't use `{audience_context}`, it simply doesn't include the placeholder — `.format()` with unused kwargs is harmless if we use a safe format approach.

**Implementation note:** Use `string.Formatter().vformat()` with a default-empty mapping, or just pass the values and have profiles decide whether to interpolate them.

---

### 5. "all" as a sentinel string, not a real profile

**Decision:** In `runner.py`, `if config.blog.prompt_profile == "all": profiles = list(PROFILES.values())` else look up the single named profile.

**Why:** "all" is a runtime convenience, not a profile definition. Registering it in `PROFILES` would complicate the lookup and mean `BlogWriter` could be asked to use an undefined profile object. Keeping it as a special case in `runner.py` is explicit and easy to find.

---

### 6. Output to `{output_dir}/{profile_name}/`

**Decision:** Always include profile name as a subdirectory, even when running a single profile.

**Why:** Consistent structure makes comparison scripts and Jekyll config simpler. `data/blog-posts/journalist/` and `data/blog-posts/practitioner/` are always present and meaningful. If the profile name changes, the output location changes predictably.

---

### 7. `BLOG_POST_SYSTEM` and `BLOG_POST_USER` move out of `src/blog/prompts.py`

**Decision:** Remove them from `prompts.py` and move them into `journalist.py`. `prompts.py` retains only `RELEVANCE_RANKING_*`.

**Why:** Having the same prompts in two places (prompts.py and journalist.py) is confusing. The profile files are the authoritative home. `RELEVANCE_RANKING_*` stays shared because ranking is not profile-specific (yet).

## Risks / Trade-offs

- **Profile proliferation**: Easy to add profiles means teams may accumulate many over time. Mitigation: keep `PROFILES` registry visible; document in CLAUDE.md that profiles live in `src/blog/profiles/`.
- **Format string injection errors**: If a profile's `blog_system` uses `{some_variable}` that isn't supplied, `.format()` will raise `KeyError`. Mitigation: use a safe format helper that ignores unknown placeholders, or document the supported variables clearly.
- **"all" is slow**: Running N profiles × M items × L languages is multiplicative. For 2 profiles, 4 items, 1 language = 8 blog post generations. Acceptable for comparison runs; document it.

## Migration Plan

1. Create `src/blog/profiles/` subpackage
2. Move current `BLOG_POST_SYSTEM/USER` into `journalist.py` as a `BlogPromptProfile`
3. Write `practitioner.py` with new prompts
4. Update `BlogWriter` to accept and use a profile
5. Update `runner.py` to resolve profiles from config
6. Update `BlogConfig` with new fields
7. Remove `BLOG_POST_*` from `prompts.py`
8. Test single profile run and "all" run

No data migrations. Existing blog post files are unaffected (they live under `data/blog-posts/` without a profile subdirectory — new runs will write to `data/blog-posts/{profile}/`).

## Open Questions

- Should `docs/_posts/` also be profile-scoped (`docs/_posts/{profile}/`)? Or always write Jekyll posts from the "publish" profile only?
