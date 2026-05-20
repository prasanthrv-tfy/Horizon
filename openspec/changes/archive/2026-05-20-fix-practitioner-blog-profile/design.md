## Context

The practitioner profile in `src/blog/profiles/practitioner.py` defines four prompts: `blog_system`, `blog_user`, `research_system`, `research_user`. The current `blog_system` gives the model a numbered 7-section template. The model fills the template faithfully — which is the problem. Every post gets TL;DR, What technically changed, How it works, What this means for practitioners (always numbered 1–5), How to use it, Caveats (always numbered 1–5), and Sources, regardless of whether the story warrants that shape.

Additionally, the user prompt labels input fields as `**News Item:**` and passes internal pipeline fields (`Score`, `Reason`) verbatim, both of which leak into post body text.

The research prompts are not implicated — they produce good, targeted search queries and are unchanged.

## Goals / Non-Goals

**Goals:**
- Replace the section template with writing principles: what to do, what never to do, and how to open a post
- Eliminate prompt vocabulary that bleeds into body text ("practitioner", "news item")
- Ban specific AI-tell patterns by name in the prompt
- Remove the `Score`/`Reason` pipeline fields from the user prompt — the model doesn't need to know the internal score
- Restrict code examples to real, runnable code only; no pseudocode, no illustrative snippets
- Keep the post length guidance (800–1500 words) and the no-background-padding rule

**Non-Goals:**
- Changing the journalist profile
- Changing `BlogPromptProfile` structure, `BlogWriter`, runner, or any other code
- Changing research prompts
- Changing output format (Markdown, Jekyll front matter)

## Decisions

### Replace numbered template with writing principles

**Decision**: Remove the explicit numbered section list from `blog_system` and replace with a set of affirmative principles (what to do) and a negative list (what never to write).

**Rationale**: The template is the direct cause of structural uniformity. Principles constrain behavior without prescribing shape — the model finds the structure that fits the story, which is what human writers do. A policy post naturally has different sections than a model release post.

**Alternative considered**: Soften the template (make sections optional). Rejected — "optional" sections still become defaults. The model satisfies the template.

### Explicit ban list for AI-tell phrases and patterns

**Decision**: Include a `**Never write:**` block in `blog_system` that names specific forbidden patterns: TL;DR as a header, "My opinion:" / "Caveats" as section headers, "That matters because", "In other words", "At a high level", "From an engineering standpoint", "The interesting part is", numbered takeaway lists under a "What this means" heading, and the word "practitioner" in body text.

**Rationale**: LLMs respond well to explicit negative constraints. Vague guidance ("avoid AI-sounding language") is insufficient; specific phrase bans are much more effective.

### Remove Score/Reason from user prompt

**Decision**: Strip `Score: {score}/10` and `Reason: {reason}` from the `blog_user` template.

**Rationale**: These are internal pipeline metadata. Passing them to the model causes it to treat the reason as framing and sometimes echo it. The model should derive its own take from the content and web research, not amplify the analyzer's one-line reason.

### Rename "News Item" label to "Source"

**Decision**: Change the `**News Item:**` header in `blog_user` to `**Source:**`.

**Rationale**: The phrase "news item" appears verbatim in generated post bodies. The model picks up prompt vocabulary. A neutral label ("Source") is less likely to be mirrored.

### Code examples: real or absent

**Decision**: Replace "Include actual commands, API signatures, or code snippets wherever they exist in the source material or can be reasonably inferred" with "Only include code if it is real and runnable — exact API calls, commands, or snippets from source material. No pseudocode, no illustrative placeholders."

**Rationale**: "Can be reasonably inferred" produces pedagogical pseudocode that looks authoritative but isn't useful. Practitioners distrust code that doesn't actually run.

## Risks / Trade-offs

- **Less structured output** → Posts may occasionally lack clear section breaks if the model interprets "no template" too freely. Mitigation: the principles still require a strong opening sentence and explicit source links at the end.
- **Model may drift back to habits** → Without template enforcement, some template-like patterns may persist. Mitigation: the explicit ban list targets the most common ones by name.
- **Short posts for thin stories** → Without sections to fill, a low-information story (like the Dell/OpenAI partnership) may produce a very short post. This is actually correct behavior — the current template padded thin stories to match section count.
