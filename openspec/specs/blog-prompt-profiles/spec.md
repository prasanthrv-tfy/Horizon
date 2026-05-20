### Requirement: BlogPromptProfile bundles all prompts for a profile
The system SHALL define a `BlogPromptProfile` dataclass with fields `name: str`, `blog_system: str`, `blog_user: str`, `research_system: str`, and `research_user: str`.

#### Scenario: Profile has all required fields
- **WHEN** a `BlogPromptProfile` is instantiated
- **THEN** it exposes `name`, `blog_system`, `blog_user`, `research_system`, and `research_user` as attributes

---

### Requirement: Profiles are registered in a central registry
The system SHALL maintain a `PROFILES: dict[str, BlogPromptProfile]` registry in `src/blog/profiles/__init__.py`. Each registered profile SHALL have a unique name matching its dict key.

#### Scenario: Registered profiles are accessible by name
- **WHEN** `PROFILES["journalist"]` is accessed
- **THEN** it returns the journalist `BlogPromptProfile` instance

#### Scenario: Registered profiles are accessible by name (practitioner)
- **WHEN** `PROFILES["practitioner"]` is accessed
- **THEN** it returns the practitioner `BlogPromptProfile` instance

---

### Requirement: Each profile lives in its own Python file
The journalist profile SHALL live in `src/blog/profiles/journalist.py` and the practitioner profile SHALL live in `src/blog/profiles/practitioner.py`. Each file SHALL export a module-level `PROFILE` variable of type `BlogPromptProfile`.

#### Scenario: Journalist profile file is importable
- **WHEN** `from src.blog.profiles.journalist import PROFILE` is executed
- **THEN** `PROFILE.name == "journalist"` and all prompt fields are non-empty strings

#### Scenario: Practitioner profile file is importable
- **WHEN** `from src.blog.profiles.practitioner import PROFILE` is executed
- **THEN** `PROFILE.name == "practitioner"` and all prompt fields are non-empty strings

---

### Requirement: BlogConfig exposes profile selection and context injection fields
`BlogConfig` SHALL have `prompt_profile: str = "journalist"`, `audience_context: str = ""`, and `platform_context: str = ""` fields.

#### Scenario: Default profile is journalist
- **WHEN** `BlogConfig()` is instantiated with no arguments
- **THEN** `prompt_profile == "journalist"`

#### Scenario: Context fields default to empty string
- **WHEN** `BlogConfig()` is instantiated with no arguments
- **THEN** `audience_context == ""` and `platform_context == ""`

---

### Requirement: BlogWriter uses the profile's prompts end-to-end
`BlogWriter` SHALL accept a `BlogPromptProfile` at construction time. It SHALL use `profile.blog_system` and `profile.blog_user` for blog post generation and `profile.research_system` and `profile.research_user` for web search query extraction, injecting `audience_context` and `platform_context` into the system prompt before calling the AI client.

#### Scenario: Profile system prompt is injected with context
- **WHEN** `BlogWriter` generates a post with `audience_context="ML engineers"` and `platform_context="TrueFoundry"` 
- **THEN** the AI client receives a system prompt that contains those values

#### Scenario: Profile research prompts are used for query extraction
- **WHEN** `BlogWriter._extract_concepts` is called on an item
- **THEN** the AI client receives `profile.research_system` as the system prompt (not the shared `CONCEPT_EXTRACTION_SYSTEM`)

---

### Requirement: "all" profile sentinel runs every registered profile
When `BlogConfig.prompt_profile == "all"`, the runner SHALL execute blog generation for every profile in `PROFILES`, producing output for each.

#### Scenario: "all" generates output for each profile
- **WHEN** `horizon-blog` is run with `prompt_profile: "all"`
- **THEN** blog posts are written under both `{output_dir}/journalist/` and `{output_dir}/practitioner/`

---

### Requirement: Practitioner profile blog_system prompt uses writing principles, not a section template
The practitioner profile's `blog_system` prompt SHALL instruct the model using writing principles (what to do, what never to write) rather than a numbered section template. It SHALL NOT prescribe section names or order. It SHALL include an explicit ban list of AI-tell phrases and structural patterns that must not appear in the output.

#### Scenario: Post structure varies by story type
- **WHEN** the practitioner profile generates a post about a policy announcement
- **THEN** the post structure differs from one generated about a model release (different sections, different flow)

#### Scenario: Banned phrases do not appear in output
- **WHEN** the practitioner profile generates any blog post
- **THEN** the post body does not contain the phrases "TL;DR", "My opinion:", "Caveats", "That matters because", "In other words", "At a high level", or the word "practitioner"

#### Scenario: No numbered takeaway lists
- **WHEN** the practitioner profile generates any blog post
- **THEN** the post does not contain a section headed "What this means for practitioners" with numbered sub-items

---

### Requirement: Practitioner profile blog_user prompt does not expose internal pipeline metadata
The practitioner profile's `blog_user` prompt SHALL NOT include `Score` or `Reason` fields from the pipeline analyzer. The input label for the news source SHALL be `**Source:**`, not `**News Item:**`.

#### Scenario: "news item" phrase does not appear in post body
- **WHEN** the practitioner profile generates any blog post
- **THEN** the phrase "news item" does not appear in the post body text

#### Scenario: Score and reason fields are absent from the prompt
- **WHEN** `BlogWriter` constructs the user prompt using the practitioner profile
- **THEN** the formatted prompt does not contain a `Score:` or `Reason:` line

---

### Requirement: Practitioner profile only includes real, runnable code examples
The practitioner profile's `blog_system` prompt SHALL instruct the model to include code only when exact API calls, commands, or snippets are available from the source material. It SHALL explicitly prohibit pseudocode and illustrative placeholder snippets.

#### Scenario: No pseudocode in posts with thin technical detail
- **WHEN** the practitioner profile generates a post about an announcement with no published API or code
- **THEN** the post contains no code block, rather than a pseudocode approximation

---

### Requirement: Output is scoped to a profile subdirectory
Blog posts SHALL be written to `{output_dir}/{profile_name}/` and Jekyll posts to `docs/_posts/{profile_name}/`. This applies whether one profile or all profiles are run.

#### Scenario: Single profile output is profile-scoped
- **WHEN** `horizon-blog` is run with `prompt_profile: "practitioner"`
- **THEN** posts are written to `{output_dir}/practitioner/` not directly to `{output_dir}/`

#### Scenario: Multi-profile outputs do not overwrite each other
- **WHEN** `horizon-blog` is run with `prompt_profile: "all"`
- **THEN** journalist posts are in `{output_dir}/journalist/` and practitioner posts are in `{output_dir}/practitioner/` with no files overwriting each other
