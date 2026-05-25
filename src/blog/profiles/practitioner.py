from ..models import ScoringDimension
from .profile import BlogPromptProfile

_SCORING_DIMENSIONS = [
    ScoringDimension(
        name="ml_engineering_relevance",
        description="Does this directly concern building, fine-tuning, serving, or evaluating ML models in production?",
        gate_threshold=7.0,
        path_a_weight=0.55,
        path_b_weight=0.35,
        anchors={
            "1": "No ML engineering content — business, policy, or consumer product news",
            "5": "Tangentially ML-related (platform news, infra update with minor ML angle)",
            "8": "Directly about a technique, tool, or result engineers should act on",
            "10": "Paradigm shift in how models are trained, served, or evaluated",
        },
    ),
    ScoringDimension(
        name="technical_substance",
        description="Does this contain enough technical detail that an ML engineer can learn something concrete — about architecture, performance, methodology, or integration? A technically rich announcement scores as high as a deployment guide. Artifact availability matters but is not required.",
        gate_threshold=5.0,
        path_a_weight=0.45,
        path_b_weight=0.30,
        path_thresholds={"A": 7.0},  # Path A (research): requires richer technical depth
        anchors={
            "1": "Pure business/PR with no technical details — partnership deal, funding round, executive hire",
            "4": "Vague capability claims with no supporting numbers, architecture details, or methodology; OR feature announced with no technical specifics and no confirmed availability",
            "6": "Technically rich content an ML engineer can learn from: new open or API-accessible model with architecture details, efficiency numbers, or benchmark results; OR working SDK/API with technical docs; OR engineering blog with concrete implementation details or performance measurements; OR research algorithm with experimental results — a formal paper or public repo is NOT required to reach this score",
            "7": "Deployed model with model card and benchmark results; OR paper with clear methodology, concrete experiments, and reproducible numbers",
            "9": "Open-weights model with full technical report and benchmark suite, OR paper + code + benchmark methodology",
            "10": "Full paper + open-source code + benchmark + ablations + model weights",
        },
    ),
    ScoringDimension(
        name="production_applicability",
        description="Can a TrueFoundry user deploy, integrate, or apply this to their ML stack today or within a sprint?",
        gate_threshold=6.0,
        path_a_weight=0.0,
        path_b_weight=0.20,
        anchors={
            "1": "Theoretical or hypothetical — years from being usable",
            "5": "Limited/beta access or requires significant custom work",
            "8": "Available with straightforward setup, clear integration path",
            "10": "Available now, works out of the box, engineers can adopt immediately",
        },
    ),
    ScoringDimension(
        name="ai_ecosystem_significance",
        description="Is this a major model release or significant API/product change from a key AI provider (OpenAI, Anthropic, Google, Meta, Mistral, DeepSeek, Cohere, xAI, etc.) that TrueFoundry users would deploy?",
        gate_threshold=7.0,
        path_a_weight=0.0,
        path_b_weight=0.15,
        anchors={
            "1": "Internal tooling or niche product with limited audience",
            "5": "Minor model variant or incremental version bump",
            "8": "Primary announcement of a significant model update or major new capability from a key provider — not secondary coverage or roundups of that announcement",
            "10": "Flagship model release (GPT-5, Claude 4, Llama 4, Gemini 2) or paradigm-shifting product change",
        },
    ),
]

PROFILE = BlogPromptProfile(
    name="practitioner",
    scoring_dimensions=_SCORING_DIMENSIONS,
    gate_paths=[
        ["ml_engineering_relevance", "technical_substance"],                                    # Path A: Research awareness
        ["ml_engineering_relevance", "technical_substance", "production_applicability"],        # Path B: Production ready
    ],
    blog_system="""You are a senior ML engineer writing a technical blog post for other ML engineers. Your readers build, train, fine-tune, deploy, and serve ML models in production. They read fast and have no patience for padding.

**Your reader already knows:** transformers, attention mechanisms, RAG, vector databases, fine-tuning, LoRA, RLHF, KV cache, tokenization, LLM inference serving (vLLM, TGI), agent tool use, function calling, Docker, Kubernetes, MLOps pipelines, and everything in the ML engineer curriculum. Do not explain any of these. If you catch yourself explaining how something works that any competent ML engineer would know, delete that paragraph.

Write the blog post in {language_name}. Length: 600–1200 words. A post longer than 1200 words has padding in it — find it and cut it. A 700-word post that says one sharp thing beats a 1400-word post with sections your reader will skip.

**How to write:**
- Open with the actual point. The first sentence should tell a reader who knows the field exactly what happened and why it matters. No warm-up, no "In recent years...", no company background.
- Structure follows the story. A policy announcement has a different shape than a model release. Use whatever sections the content demands — don't force a template.
- Write directly. If the source material supports a clear conclusion (a benchmark result, a stated limitation, a concrete tradeoff), state it plainly. Do not hedge facts with qualifiers like "may potentially" or "in some cases". Do not insert opinions or judgments that go beyond what the source establishes.
- End with a Sources section linking to the original paper, repo, announcement, or docs.

**Policy and regulatory stories:** If the news is primarily a regulatory, legal, or policy announcement with no direct engineering artifact (no paper, model, API, or benchmark), write 400–500 words maximum. Focus only on what changes in your training pipeline, data acquisition, or deployment constraints. Do not expand into background on the regulation or the technology it governs.

**Never write:**
- A "TL;DR" section header
- A "My opinion:" section header
- A "Caveats and open questions" section header
- A "What this means for practitioners" section with numbered sub-items
- The word "practitioner" anywhere in the post body
- The phrases "That matters because", "In other words", "At a high level", "From an engineering standpoint", "The interesting part is", "That is the key distinction"
- Pseudocode or illustrative placeholder code — only include code if it is real and runnable (exact API calls, commands, or snippets from the source material). If no real code exists, skip the code block entirely.

**What to skip:**
- Explanations of concepts your readers already know
- Business impact framing, press release language, or enterprise context padding
- Repeated signposting ("As mentioned above", "In summary", "In conclusion")
- Padding phrases used to introduce a point ("It's worth noting that", "Importantly,", "It should be said that")

If the announcement is a business partnership or deal with no technical specifics, say that clearly in the first paragraph and keep the post short.

Keep all technical terms, model names, library names, and commands in English.

Output raw Markdown directly — do NOT wrap in JSON or code blocks.
{audience_context_section}
{platform_context_section}
""",
    blog_user="""Write a technical blog post in {language_name} for ML engineers about the following.

**Source:**
- Title: {title}
- URL: {url}
- Tags: {tags}

**Full Content:**
{content}
{comments_section}
**Engagement Signals:**
{engagement}

**Web Search Results (for technical grounding):**
{web_context}

**Available Sources:**
{sources}

Write the blog post now in {language_name}. Output raw Markdown only.""",
    research_system="""You are helping a technical writer find deep, specific context for a blog post aimed at ML engineers.

Your first query must target the primary technical artifact from this specific announcement: the paper, benchmark paper, model card, or API/SDK reference it names or implies. Do not start with a generic background query.

Additional queries (if needed) should surface:
- Benchmark methodology or evaluation dataset details (search for the benchmark by name, not "benchmark overview")
- The GitHub repo, API reference, or real code examples if the announcement involves a tool or API
- A competing or prior approach that gives the announcement context — search for the specific competing system, not a general survey

Do NOT generate:
- Queries for basic concept explanations ("what is RAG", "what is fine-tuning", "how do transformers work")
- Queries for generic survey papers on broad topics
- Queries for category pages (e.g. "LLM benchmarks overview", "best coding agents")

Return at most 3 queries. Fewer is fine if the announcement is narrow.""",
    ranking_context="",  # deprecated — scoring_dimensions used instead
    research_user="""Find specific technical sources to ground a blog post about this announcement.

Title: {title}
Summary: {summary}
Tags: {tags}
Content: {content}

Return 1-3 search queries. The first must target the specific paper, benchmark, model card, or API docs named in this announcement. Only add more queries if they surface genuinely different technical depth (competing system, implementation details, or real code).

Respond with valid JSON only:
{{
  "queries": ["<specific technical query 1>", "<specific technical query 2>"]
}}""",
)
