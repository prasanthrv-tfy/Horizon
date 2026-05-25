## ADDED Requirements

### Requirement: BlogPromptProfile carries a ranking_context field
`BlogPromptProfile` SHALL include an optional `ranking_context: str` field (default empty string) that describes, in 2–4 sentences, what makes a news item relevant for that profile's audience. This field is used exclusively during item ranking, not during post writing.

#### Scenario: ranking_context present on profile
- **WHEN** a `BlogPromptProfile` is instantiated with a non-empty `ranking_context`
- **THEN** the field is accessible on the profile object and can be injected into ranking prompts

#### Scenario: ranking_context absent (default)
- **WHEN** a `BlogPromptProfile` is instantiated without `ranking_context`
- **THEN** the field defaults to an empty string and ranking falls back to generic criteria

---

### Requirement: rank_by_relevance accepts optional audience context
The `rank_by_relevance()` function SHALL accept an optional `audience_context: str` parameter. When provided and non-empty, it SHALL be injected into the ranking prompt so the LLM ranks items against that audience's relevance criteria rather than generic newsworthiness criteria.

#### Scenario: Audience context injected into prompt
- **WHEN** `rank_by_relevance()` is called with a non-empty `audience_context`
- **THEN** the ranking prompt includes the audience context and instructs the LLM to weight item relevance for that specific audience

#### Scenario: No audience context — generic fallback
- **WHEN** `rank_by_relevance()` is called without `audience_context` or with an empty string
- **THEN** the ranking prompt uses generic criteria (same behavior as before this change)

---

### Requirement: Ranking runs independently per profile
The blog runner SHALL call `rank_by_relevance()` once per profile (inside the profile loop) rather than once globally, passing each profile's `ranking_context` so each profile independently selects its top-N items.

#### Scenario: Two profiles produce different ranked orders
- **WHEN** `horizon-blog` runs with `prompt_profile: "all"` and profiles have different `ranking_context` values
- **THEN** the items selected for each profile may differ, reflecting each profile's audience relevance criteria

#### Scenario: Single profile runs ranking once
- **WHEN** `horizon-blog` runs with a single profile
- **THEN** `rank_by_relevance()` is called exactly once, with that profile's `ranking_context`

#### Scenario: Selected items logged per profile
- **WHEN** items are selected for a profile after ranking
- **THEN** the console output identifies which items were selected for that profile
