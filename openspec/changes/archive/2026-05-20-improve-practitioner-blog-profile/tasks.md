## 1. Practitioner blog_system prompt

- [ ] 1.1 Replace vague audience description with explicit "your reader already knows" enumeration (transformers, RAG, LoRA, RLHF, KV cache, vLLM, TGI, agent tool use, function calling, Docker, Kubernetes) and add self-check instruction to delete any paragraph explaining a listed concept
- [ ] 1.2 Reframe word count from "Target 800–1500 words" to "600–1200 words; a post longer than 1200 has padding — find it and cut it"
- [ ] 1.3 Add policy/regulatory story short-circuit: if no direct engineering artifact (paper, model, API, benchmark), cap at 400–500 words and focus on pipeline/deployment impact only
- [ ] 1.4 Strengthen position-taking instruction: if a balanced "on one hand / on the other hand" paragraph appears, cut it and pick the side the evidence supports

## 2. Practitioner research prompts

- [ ] 2.1 Update `research_system` to require the first query target the specific paper, benchmark, model card, or API/SDK reference named in the announcement
- [ ] 2.2 Add negative constraints to `research_system` prohibiting queries for generic survey papers, category pages, and basic concept explanations
- [ ] 2.3 Update `research_user` to reinforce that the first query must target the specific named artifact

## 3. Writer content window

- [ ] 3.1 In `src/blog/writer.py` `_extract_concepts`, change `content_text[:1000]` to `content_text[:2500]`

## 4. Verification

- [ ] 4.1 Run `uv run horizon-blog --profile practitioner` and confirm all posts are under 1200 words
- [ ] 4.2 Confirm the Databricks-style post sources include the specific named benchmark paper rather than generic survey links
- [ ] 4.3 Confirm a policy/regulatory story post is under 500 words
