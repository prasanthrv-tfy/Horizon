## Context

The practitioner profile (`src/blog/profiles/practitioner.py`) is a prompt-only configuration: four string fields (`blog_system`, `blog_user`, `research_system`, `research_user`) consumed by `BlogWriter`. The writer calls the research prompts to generate DuckDuckGo queries, executes those queries, and passes the results into the blog generation prompt.

Analysis of four generated posts revealed consistent failure modes: posts 20–40% over the word ceiling, explanations of concepts the target audience knows by heart, research queries returning generic survey papers instead of the specific artifact named in the announcement, and policy stories expanding to the same length as technical ones.

All failure modes trace to two locations: the prompt strings in `practitioner.py` and a single line in `writer.py` that truncates article content before passing it to the research query generator.

## Goals / Non-Goals

**Goals:**
- Posts from the practitioner profile fit within 1,200 words
- Research queries surface the specific paper, benchmark, model card, or API named in the announcement
- Policy/regulatory stories are capped at 500 words and focus on pipeline impact
- Posts do not explain concepts ML engineers already know
- The journalist profile and all shared infrastructure are untouched

**Non-Goals:**
- Changing the `BlogPromptProfile` data model or the profile registry
- Modifying the runner, storage, or delivery logic
- Introducing evaluation tooling or automated quality checks
- Changing how the journalist profile behaves

## Decisions

**Decision: All changes are prompt-only except one line in writer.py**

Alternatives considered: adding a post-generation word-count check and re-prompting if over limit; adding a classifier to detect story type before generation. Both add latency and complexity. The prompt is the right place to set expectations — the model is capable of following word count instructions when framed as a quality signal rather than a target range. The 1,000→2,500 char increase in `writer.py` is the minimum code change needed to give the research step enough context to identify specific benchmark/API names.

**Decision: Explicit "already knows" list rather than relying on audience description**

The vague "fluent in PyTorch, Kubernetes..." description leaves the ceiling undefined. An explicit enumeration (transformers, RAG, LoRA, vLLM/TGI, etc.) gives the model a concrete check: "would a competent ML engineer already know this?" It also makes the self-check instruction ("if you catch yourself explaining X, delete that paragraph") actionable.

**Decision: Policy story short-circuit is in blog_system, not the runner**

Routing by story type at the runner level would require a classification step before generation. Embedding the rule in the system prompt is simpler and keeps the runner logic stable. The rule is precise: "no direct engineering artifact (no paper, model, API, or benchmark)" triggers the 400–500 word cap.

**Decision: Research query anchoring via instruction, not schema change**

The research query format (JSON with `queries` array) is unchanged. The improvement is in what queries the model generates: the first must target the specific named artifact. This is enforced through prompt instruction, not output schema validation.

## Risks / Trade-offs

- **Risk**: The 600–1200 word ceiling may cause the model to truncate genuinely dense technical stories prematurely. → Mitigation: the lower bound is 600, giving enough room for depth; the instruction frames length as a quality check, not an arbitrary cut.
- **Risk**: The "already knows" list will go stale as the field evolves. → Mitigation: the list is illustrative, not exhaustive — the model generalises from examples. Low maintenance burden.
- **Risk**: Policy story short-circuit may misfire on announcements that are partly policy, partly technical. → Mitigation: the trigger condition is "no direct engineering artifact" — if there's a model card, API, or benchmark alongside the policy news, the full treatment applies.
