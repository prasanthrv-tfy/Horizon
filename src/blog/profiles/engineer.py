from src.blog.models import GatePath, PathDimensionConfig, ScoringDimension
from .profile import BlogPromptProfile

_SCORING_DIMENSIONS = [
    ScoringDimension(
        name="ml_engineering_relevance",
        description="Does this directly concern building, fine-tuning, serving, evaluating, or securing ML models and agent systems in production?",
        anchors={
            "1": "No ML engineering content — business, policy, or consumer product news",
            "3": "Enterprise partnership, vendor deal, or distribution agreement where the subject is ML but the content is business/PR — even if benchmark results are mentioned in passing, no engineering artifact (paper, model weights, API, or technical docs) is provided that an engineer can act on",
            "4": "ML applied to an unrelated domain (mathematics, law, biology, climate) where the content focuses on the domain result, not on the ML technique or engineering method — the finding cannot be transferred to building or operating ML systems",
            "5": "Tangentially ML-related (platform news, infra update with minor ML angle); OR enterprise distribution announcement where an existing model is made available through a new vendor/channel with no new technical content; OR secondary news coverage, explainer article, or roundup about ML topics — even if the underlying topic is important, no primary technical artifact (paper, model weights, API, or technical docs) is provided that an engineer can act on",
            "8": "Directly about a technique, tool, result, or safety/reliability finding that engineers building or operating ML systems should act on or be aware of",
            "10": "Paradigm shift in how models are trained, served, or evaluated",
        },
    ),
    ScoringDimension(
        name="technical_substance",
        description="Does this contain enough technical detail that an ML engineer can learn something concrete — about architecture, performance, methodology, or integration? A technically rich announcement scores as high as a deployment guide. Artifact availability matters but is not required.",
        anchors={
            "1": "Pure business/PR with no technical details — partnership deal, funding round, executive hire",
            "4": "Vague capability claims with no supporting numbers, architecture details, or methodology; OR pure announcement with no confirmed availability and no technical specifics",
            "5": "Research or lab blog post that describes a method, finding, or benchmark at a conceptual level — some methodology described, but key implementation details, reproducible numbers, or evaluation protocol are not provided",
            "6": "Technically rich content an ML engineer can learn from: new open or API-accessible model with architecture details, efficiency numbers, or benchmark results; OR working SDK/API with technical docs; OR engineering blog with concrete implementation details or performance measurements; OR research algorithm with experimental results — a formal paper or public repo is NOT required to reach this score",
            "7": "Deployed model with model card and benchmark results; OR paper with clear methodology, concrete experiments, and reproducible numbers",
            "9": "Open-weights model with full technical report and benchmark suite, OR paper + code + benchmark methodology",
            "10": "Full paper + open-source code + benchmark + ablations + model weights",
        },
    ),
    ScoringDimension(
        name="production_applicability",
        description="Can a TrueFoundry user deploy, integrate, or apply this to their ML stack today or within a sprint?",
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
        anchors={
            "1": "Internal tooling or niche product with limited audience",
            "5": "Minor model variant or incremental version bump",
            "6": "Specific model, tool, or feature released directly by a key AI provider (OpenAI, Anthropic, Google, Meta, Mistral, etc.) that serves a focused production need — e.g. a specialised open-weight model, a safety/privacy tool, or an incremental API addition. Academic papers, third-party tools, and research from universities or non-AI-provider companies do NOT qualify for this score regardless of usefulness.",
            "7": "Major SDK release, significant new API capability, or important developer tooling update from a key provider that meaningfully changes how engineers build with these systems — e.g. a new agent framework, code execution sandbox, or retrieval API from OpenAI/Anthropic/Google/Meta",
            "8": "Primary announcement of a significant model update or major new capability from a key provider — not secondary coverage or roundups of that announcement",
            "10": "Flagship model release (GPT-5, Claude 4, Llama 4, Gemini 2) or paradigm-shifting product change",
        },
    ),
    ScoringDimension(
        name="engineering_insight",
        description="Does this advance an ML engineer's understanding of how to design, build, evaluate, or operate ML systems — independent of whether it is immediately deployable? Score on what a practitioner learns, not on production readiness.",
        anchors={
            "1": "No engineering insight — pure business news, market commentary, or consumer product update with nothing an engineer can learn",
            "4": "Broadly interesting to ML people but does not advance engineering knowledge — ML applied to an unrelated domain where the result is domain-specific and cannot be transferred; OR regulatory, legal, or market news with no engineering implication; OR a bug bounty announcement, red-team program launch, or safety initiative call-to-action where no findings have been disclosed yet — the topic may be important, but there is nothing an engineer can learn until actual results are published",
            "6": "Directly informs how practitioners should think about designing, evaluating, or operating ML or agent systems — concrete findings or methodology that updates engineering judgment, even if not deployable today",
            "8": "Hands-on research with clear engineering implications that practitioners should incorporate into their workflow or mental model — e.g. new failure mode in multi-agent systems, inference scaling tradeoff, alignment evaluation methodology",
            "10": "Paradigm-shifting engineering insight with validated results that changes how ML systems should be built or operated",
        },
    ),
]

PROFILE = BlogPromptProfile(
    name="engineer",
    scoring_dimensions=_SCORING_DIMENSIONS,
    gate_paths=[
        GatePath(
            name="engineering_applicability",
            dimensions=[
                PathDimensionConfig(dimension="ml_engineering_relevance", weight=0.35, threshold=7.0),
                PathDimensionConfig(dimension="technical_substance",       weight=0.30, threshold=5.0),
                PathDimensionConfig(dimension="production_applicability",  weight=0.20, threshold=7.0),
                PathDimensionConfig(dimension="ai_ecosystem_significance", weight=0.15, threshold=5.0),
            ],
        ),
        GatePath(
            name="technical_insights",
            dimensions=[
                PathDimensionConfig(dimension="ml_engineering_relevance", weight=0.45, threshold=8.0),
                PathDimensionConfig(dimension="technical_substance",       weight=0.30, threshold=6.0),
                PathDimensionConfig(dimension="engineering_insight",       weight=0.25, threshold=6.0),
            ],
        ),
    ],
    blog_system="""You are a senior ML engineer writing for other senior ML engineers. Your readers build, train, fine-tune, serve, and evaluate ML models in production.

**Title:** Start your output with a `# Title` line. The title is used as the CMS item name and URL slug — keep it under 70 characters. Write from a reader's perspective: name who released or published what, in third-person. Never use first-person ("Our", "We", "I") in the title.

**Your reader already knows:** transformers, attention, RAG, vector databases, fine-tuning, LoRA, RLHF, KV cache, tokenization, LLM inference serving (vLLM, TGI), agent tool use, function calling, Docker, Kubernetes, MLOps pipelines. Never explain these. If you find yourself explaining how something works that any ML engineer already knows, cut the paragraph.

**Opening:** The first 1–2 sentences must name what was released or announced and by whom. The reader is coming in cold — they don't know what the post is about until you tell them. After establishing the subject, get straight to what matters.

**Pick the right post type based on the content:**
- *Informational* — for model releases, framework releases, API/tool launches, and product updates: explain clearly what it is, what changed, and how an engineer would use or evaluate it. Your job is clarity and completeness, not opinion.
- *Analysis* — for research findings, architectural patterns, benchmark results, and industry trends: take a position. Say what you'd do, what you're skeptical of, and how this compares to existing approaches. First person is appropriate here.

Do not force opinion onto informational posts, and do not flatten analysis posts into neutral summaries.

**Length:** 500–800 words. Go longer only if the content genuinely has that depth.

**Structure:** Use headers where they help the reader navigate — a major topic shift, a distinct technical concept, or a separate model/component worth calling out. 2–3 headers is typical. Five or six headers means you're walking a feature list. Name headers after what you're actually saying, not after a document position ("What changed", "The takeaway", "What this means for your stack").

**Format rules:**
- No dedicated summary or conclusion section — "In summary", "Key takeaways", "The bottom line", "Practical takeaway", and all variants are banned. If the post builds correctly, the last paragraph is already the conclusion.
- Bullet lists are for genuinely enumerable, parallel items only — a list of supported languages, a list of API endpoints. Do not use bullets to present an argument, list implications, or enumerate reasons. Those belong in prose.
- State things directly. Don't write "The post describes...", "According to the announcement..." — just say the thing.
- Don't hedge facts, but acknowledge genuine uncertainty when details are missing from the source.
- Only include code if it's real and runnable — exact API calls, commands, or snippets from the source. No pseudocode.

**If the story is thin:** Some announcements are PR with no engineering substance. Say that clearly in the first paragraph and keep the post under 300 words.

**Policy or regulatory stories:** Cover only what changes in training pipelines, data handling, or deployment constraints. 300–400 words maximum.

Keep all technical terms, model names, library names, and commands in English. Write the post in {language_name}.

End with a Sources section. Output raw Markdown only.
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

Your first query must target the primary technical artifact from this specific announcement: the paper, benchmark, model card, or API/SDK reference it names or implies. Do not start with a generic background query.

Additional queries (if needed) should surface:
- Benchmark methodology or evaluation dataset details (search for the benchmark by name, not "benchmark overview")
- The GitHub repo, API reference, or real code examples if the announcement involves a tool or API
- A competing or prior approach that gives the announcement context — search for the specific competing system, not a general survey
- Practitioner reactions: Hacker News discussion, GitHub issues, or engineering blog posts about this release — these often surface the real-world caveats and limitations that the announcement omits

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

Return plain natural language queries only — no boolean operators (OR, AND, NOT), no quoted phrases.

Respond with valid JSON only:
{{
  "queries": ["<specific technical query 1>", "<specific technical query 2>"]
}}""",
)
