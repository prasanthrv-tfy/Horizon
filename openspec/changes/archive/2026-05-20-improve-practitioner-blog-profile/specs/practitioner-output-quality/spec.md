## ADDED Requirements

### Requirement: Practitioner posts SHALL not exceed 1200 words
The practitioner profile's `blog_system` prompt SHALL instruct the model that posts exceeding 1200 words contain padding and must be cut. The instruction SHALL frame word count as a failure signal, not a target range.

#### Scenario: Generated post is within word ceiling
- **WHEN** the practitioner profile generates a blog post for any news item
- **THEN** the post body (excluding front matter) contains no more than 1200 words

#### Scenario: Word count framing is a quality signal
- **WHEN** the `blog_system` prompt is read
- **THEN** it contains language stating that a post longer than 1200 words has padding, not a "target" range

---

### Requirement: Practitioner blog_system SHALL include an explicit audience knowledge ceiling
The practitioner profile's `blog_system` prompt SHALL include an enumerated list of concepts the reader already knows (including but not limited to: transformers, RAG, LoRA, RLHF, KV cache, vLLM, TGI, agent tool use, function calling, Docker, Kubernetes). It SHALL instruct the model to delete any paragraph that explains a concept from this list.

#### Scenario: Post does not explain RAG to the reader
- **WHEN** the practitioner profile generates a post about a RAG-related announcement
- **THEN** the post does not contain an explanation of what RAG is or how it works

#### Scenario: Post does not explain fine-tuning to the reader
- **WHEN** the practitioner profile generates a post that references fine-tuning
- **THEN** the post does not contain a definition or explanation of fine-tuning

---

### Requirement: Practitioner profile SHALL short-circuit policy stories to 400–500 words
If the news item is primarily a regulatory, legal, or policy announcement with no direct engineering artifact (no paper, model, API, or benchmark), the practitioner profile's `blog_system` prompt SHALL instruct the model to cap the post at 400–500 words and focus exclusively on pipeline, data acquisition, or deployment constraint implications.

#### Scenario: Policy story produces a short post
- **WHEN** the practitioner profile generates a post about a regulatory announcement with no associated paper, model, or API
- **THEN** the post body contains no more than 500 words

#### Scenario: Policy story focuses on pipeline impact
- **WHEN** the practitioner profile generates a post about a policy announcement
- **THEN** the post does not expand into background on the regulation or the technology it governs

---

### Requirement: Practitioner blog_system SHALL instruct the model to take a definite position
The practitioner profile's `blog_system` prompt SHALL instruct the model to avoid balanced "on one hand / on the other hand" paragraphs and instead pick the side the evidence supports.

#### Scenario: Post does not hedge with balanced paragraphs
- **WHEN** the practitioner profile generates a blog post
- **THEN** the post does not contain a paragraph that presents equal weight to opposing sides without committing to a position

---

### Requirement: Practitioner research_system SHALL anchor the first query to the primary technical artifact
The practitioner profile's `research_system` prompt SHALL instruct the model that its first search query must target the specific paper, benchmark paper, model card, or API/SDK reference named or implied by the announcement — not a background or survey query.

#### Scenario: First research query targets the named benchmark
- **WHEN** the announcement references a specific benchmark by name
- **THEN** the first generated search query includes that benchmark name

#### Scenario: First research query targets the named model card or API
- **WHEN** the announcement references a specific model version or API
- **THEN** the first generated search query targets that model card, technical report, or API docs

---

### Requirement: Practitioner research_system SHALL prohibit generic survey and category queries
The practitioner profile's `research_system` prompt SHALL explicitly prohibit queries for generic survey papers on broad topics and queries for category pages (e.g. "LLM benchmarks overview", "best coding agents").

#### Scenario: Research does not return generic survey papers
- **WHEN** the practitioner profile generates research queries for an announcement about a specific model or benchmark
- **THEN** the queries do not include terms like "overview of LLMs", "survey of language models", or category-level search terms

---

### Requirement: BlogWriter SHALL pass 2500 characters of article content to the research query generator
`BlogWriter._extract_concepts` SHALL truncate `content_text` to 2500 characters (not 1000) before passing it to the research prompt, so the model has sufficient context to identify specific benchmark names, model versions, and API references mentioned in the article body.

#### Scenario: Research query generator receives enough content to identify specific artifacts
- **WHEN** `BlogWriter._extract_concepts` is called on an item whose specific benchmark or model name appears after the first 1000 characters of content
- **THEN** the research query generator still receives that information and can generate a targeted query
