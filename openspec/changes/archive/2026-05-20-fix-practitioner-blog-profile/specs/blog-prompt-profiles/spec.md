## MODIFIED Requirements

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
