## 1. Rewrite blog_system prompt

- [x] 1.1 Remove the numbered 7-section template from `blog_system`
- [x] 1.2 Replace with affirmative writing principles: strong opening sentence, lead with the non-obvious point, structure follows story
- [x] 1.3 Add explicit `**Never write:**` ban list: TL;DR as a header, "My opinion:" / "Caveats" as section headers, "That matters because", "In other words", "At a high level", "From an engineering standpoint", "The interesting part is", numbered takeaway lists under a "What this means" heading, "practitioner" in body text
- [x] 1.4 Replace code example instruction: "only include code if it is real and runnable — exact API calls, commands, or snippets from the source material; no pseudocode, no illustrative placeholders"
- [x] 1.5 Retain: no background-padding rule, no foundational concept explanations, 800–1500 word guidance, opinionated observations encouraged, Sources section at end

## 2. Fix blog_user prompt

- [x] 2.1 Rename `**News Item:**` input label to `**Source:**`
- [x] 2.2 Remove the `Score: {score}/10` line from the user prompt template
- [x] 2.3 Remove the `Reason: {reason}` line from the user prompt template

## 3. Verify and test

- [x] 3.1 Run `uv run horizon-blog --profile practitioner` and confirm "news item" and "practitioner" do not appear in post body text
- [x] 3.2 Confirm no post contains a TL;DR header or "My opinion:" / "Caveats" section heading
- [x] 3.3 Confirm posts with thin technical detail contain no code blocks (pseudocode test)
- [x] 3.4 Confirm structure varies across posts of different story types
