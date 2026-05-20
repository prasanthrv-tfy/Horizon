## MODIFIED Requirements

### Requirement: Practitioner profile blog_system prompt uses writing principles, not a section template
The practitioner profile's `blog_system` prompt SHALL instruct the model using writing principles (what to do, what never to write) rather than a numbered section template. It SHALL NOT prescribe section names or order. It SHALL include an explicit ban list of AI-tell phrases and structural patterns that must not appear in the output. It SHALL include an explicit enumerated list of concepts the reader already knows, a word count framing as a failure signal (600–1200 words; over 1200 means padding), a policy/regulatory story short-circuit (400–500 words max, pipeline impact only), and an instruction to take a definite position rather than presenting balanced paragraphs.

#### Scenario: Post structure varies by story type
- **WHEN** the practitioner profile generates a post about a policy announcement
- **THEN** the post structure differs from one generated about a model release (different sections, different flow)

#### Scenario: Banned phrases do not appear in output
- **WHEN** the practitioner profile generates any blog post
- **THEN** the post body does not contain the phrases "TL;DR", "My opinion:", "Caveats", "That matters because", "In other words", "At a high level", or the word "practitioner"

#### Scenario: No numbered takeaway lists
- **WHEN** the practitioner profile generates any blog post
- **THEN** the post does not contain a section headed "What this means for practitioners" with numbered sub-items

#### Scenario: Post does not exceed 1200 words
- **WHEN** the practitioner profile generates a blog post for any news item
- **THEN** the post body (excluding front matter) contains no more than 1200 words

#### Scenario: Policy story is capped at 500 words
- **WHEN** the practitioner profile generates a post about a regulatory announcement with no associated paper, model, or API
- **THEN** the post body contains no more than 500 words
