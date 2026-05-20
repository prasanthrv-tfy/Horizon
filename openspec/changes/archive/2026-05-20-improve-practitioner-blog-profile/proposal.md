## Why

The practitioner blog profile was producing posts that were consistently too long (1,700–2,000 words vs. the 800–1,500 target), explained concepts ML engineers already know, sourced generic survey papers instead of the primary technical artifacts, and treated policy/regulatory stories the same as model releases. The profile's intent — sharp, dense, ML-engineer-level posts — was not being met in practice.

## What Changes

- **Tighten audience definition**: Replace the vague "fluent in PyTorch, Kubernetes..." description with an explicit "your reader already knows" list, including transformers, RAG, LoRA, RLHF, vLLM/TGI, agent tool use, and the full ML engineer curriculum. Add a self-check instruction: if a paragraph explains something any competent ML engineer would know, delete it.
- **Reframe word count as a failure signal**: Change "Target 800–1500 words" to "600–1200 words; a post longer than 1200 has padding in it — find it and cut it."
- **Add policy/regulatory story short-circuit**: If the news has no direct engineering artifact (no paper, model, API, or benchmark), cap at 400–500 words and focus exclusively on pipeline/deployment impact.
- **Strengthen position-taking guidance**: Add an explicit instruction that if the model finds itself writing a balanced "on one hand / on the other hand" paragraph, it should pick a side.
- **Anchor research queries to the primary artifact**: The first search query must target the specific paper, benchmark, model card, or API docs named in the announcement — not a background or survey query.
- **Add negative constraints to research**: Prohibit queries for generic survey papers, category pages ("LLM benchmarks overview"), and basic concept explanations.
- **Increase research content window**: Feed 2,500 characters (up from 1,000) of article content to the research query generator so it can identify specific benchmark names, model versions, and API references.

## Capabilities

### New Capabilities

- `practitioner-output-quality`: Requirements governing word count enforcement, audience knowledge ceiling, policy story handling, position-taking, and research query anchoring for the practitioner profile.

### Modified Capabilities

- `blog-prompt-profiles`: The practitioner profile's behavioral requirements are expanding — new requirements on output length, audience ceiling, policy story treatment, and research query specificity go beyond what the existing spec captures.

## Impact

- `src/blog/profiles/practitioner.py` — `blog_system`, `research_system`, `research_user` prompts
- `src/blog/writer.py` — content truncation in `_extract_concepts` (line ~197)
- No changes to journalist profile, runner, models, or any other module
