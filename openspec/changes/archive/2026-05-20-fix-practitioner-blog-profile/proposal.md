## Why

The practitioner profile generates blog posts that are obviously AI-written: every post uses the same rigid 7-section template regardless of story shape, leaks prompt vocabulary ("practitioner", "news item") into the body, and fills structural slots (TL;DR, My opinion, Caveats) mechanically even when the content doesn't warrant them. The output reads like a compliance exercise, not a practitioner's voice.

## What Changes

- Rewrite `blog_system` prompt: replace the numbered section template with writing principles that constrain tone, vocabulary, and what to avoid — letting post structure emerge from the story
- Rewrite `blog_user` prompt: rename the `**News Item:**` input label so it doesn't bleed into post language; remove the `Score`/`Reason` fields that expose internal pipeline metadata
- Remove instructions that generate pseudocode ("can be reasonably inferred") — only real, runnable code or nothing
- Explicitly ban specific AI-tell phrases and structural patterns: TL;DR as a required header, "My opinion:" / "Caveats" boilerplate, "That matters because", "In other words", numbered practitioner takeaways, and the word "practitioner" in post body
- Research prompts (`research_system`, `research_user`) are unchanged — they work well

## Capabilities

### New Capabilities
- none

### Modified Capabilities
- `blog-prompt-profiles`: the practitioner profile's prompt content is changing — what the AI is instructed to write and how it structures posts

## Impact

- `src/blog/profiles/practitioner.py` — only file changing
- No model, runner, writer, or data-model changes
- Output format (Markdown, Jekyll front matter) is unchanged
- The journalist profile is unaffected
