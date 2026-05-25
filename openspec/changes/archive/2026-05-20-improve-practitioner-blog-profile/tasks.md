## 1. Practitioner blog_system prompt

- [x] 1.1 Replace vague audience description with explicit "your reader already knows" enumeration (transformers, RAG, LoRA, RLHF, KV cache, vLLM, TGI, agent tool use, function calling, Docker, Kubernetes) and add self-check instruction to delete any paragraph explaining a listed concept
- [x] 1.2 Reframe word count from "Target 800–1500 words" to "600–1200 words; a post longer than 1200 has padding — find it and cut it"
- [x] 1.3 Add policy/regulatory story short-circuit: if no direct engineering artifact (paper, model, API, benchmark), cap at 400–500 words and focus on pipeline/deployment impact only
- [x] 1.4 Strengthen position-taking instruction: if a balanced "on one hand / on the other hand" paragraph appears, cut it and pick the side the evidence supports

## 2. Practitioner research prompts

- [x] 2.1 Update `research_system` to require the first query target the specific paper, benchmark, model card, or API/SDK reference named in the announcement
- [x] 2.2 Add negative constraints to `research_system` prohibiting queries for generic survey papers, category pages, and basic concept explanations
- [x] 2.3 Update `research_user` to reinforce that the first query must target the specific named artifact

## 3. Writer content window

- [x] 3.1 In `src/blog/writer.py` `_extract_concepts`, change `content_text[:1000]` to `content_text[:2500]`

## 4. Verification

- [x] 4.1 Run `uv run horizon-blog --profile practitioner` and confirm all posts are under 1200 words
- [x] 4.2 Confirm the Databricks-style post sources include the specific named benchmark paper rather than generic survey links
- [x] 4.3 Confirm a policy/regulatory story post is under 500 words
