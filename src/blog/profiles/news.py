from src.blog.models import GatePath, PathDimensionConfig, ScoringDimension
from .profile import BlogPromptProfile

_SCORING_DIMENSIONS = [
    ScoringDimension(
        name="significance",
        description="How broadly significant is this development for the AI/tech landscape? Does it affect many people, products, or industries?",
        anchors={
            "1": "Niche announcement affecting a tiny audience",
            "5": "Noteworthy for a specific community but limited broader impact",
            "8": "Affects many users, products, or industries in a meaningful way",
            "10": "Industry-defining event — affects everyone in the tech ecosystem",
        },
    ),
    ScoringDimension(
        name="newsworthiness",
        description="Is this timely, original, and genuinely new? Is it a primary announcement rather than derivative commentary?",
        anchors={
            "1": "Old news resurfacing or pure opinion with no new facts",
            "5": "Secondary coverage of a genuine event with some new angle",
            "8": "Primary announcement, breaking news, or original reporting",
            "10": "Major breaking development from the primary source, first of its kind",
        },
    ),
    ScoringDimension(
        name="narrative_clarity",
        description="Is there a clear, compelling story a non-expert reader can follow? Can the 'why it matters' be explained accessibly?",
        anchors={
            "1": "Highly technical or jargon-heavy with no accessible angle",
            "5": "Story exists but requires significant background to appreciate",
            "8": "Clear narrative with obvious stakes a general reader would understand",
            "10": "Compelling human or societal story that writes itself for any audience",
        },
    ),
]

PROFILE = BlogPromptProfile(
    name="news",
    scoring_dimensions=_SCORING_DIMENSIONS,
    gate_paths=[
        GatePath(
            name="news_stories",
            dimensions=[
                PathDimensionConfig(dimension="significance",       weight=0.45, threshold=6.0),
                PathDimensionConfig(dimension="newsworthiness",     weight=0.35, threshold=5.0),
                PathDimensionConfig(dimension="narrative_clarity",  weight=0.20, threshold=4.0),
            ],
        ),
    ],
    blog_system="""You are an expert technology journalist and technical writer. Your job is to write a comprehensive, well-structured blog post about a significant tech news item.

**Title:** Start your output with a `# Title` line. The title is used as the CMS item name and URL slug — keep it under 70 characters. Write from a reader's perspective: name who released or announced what, in third-person. Never use first-person ("Our", "We", "I") in the title.

Write the blog post in {language_name}. The post should be 800-1500 words and follow this structure:

1. **Headline**: A clear, engaging headline that captures the essence of the news
2. **What Happened / What's New**: Lead with the key news — what changed, what was announced, what breakthrough was made. Be specific with names, versions, numbers, dates.
3. **Why It Matters / Significance**: Explain the broader impact. Who is affected? How does this fit into industry trends? Why should readers care?
4. **Technical Details and Key Points**: Dive into the technical specifics that a technically-minded reader would find valuable. Include limitations, caveats, and notable implementation details.
5. **Background Context**: Provide enough background for a reader without deep domain expertise to understand the news. Explain key concepts, technologies, or prior art.
6. **Community Reaction**: If community comments are provided, summarize the sentiment — agreements, disagreements, concerns, notable insights.
7. **Looking Ahead / Implications**: What might this lead to? What are the open questions? What should readers watch for?
8. **Sources and References**: Link back to the original source and any web search results you relied on.

**Guidelines:**
- Base your writing on the provided content, comments, and web search results — do NOT fabricate information
- Use a professional but accessible tone — informative, not sensational
- Include code snippets or technical examples only if they appear in the source material
- Format as clean Markdown with proper headings (##), lists, bold text, and links
- If writing in Chinese (zh), use Simplified Chinese (简体中文). Keep technical abbreviations, acronyms, and widely-used proper nouns in their original English form (e.g. "GPT-4", "CUDA", "Rust").
- Output raw Markdown directly — do NOT wrap in JSON or code blocks
""",
    blog_user="""Write a comprehensive blog post in {language_name} about the following news item.

**News Item:**
- Title: {title}
- URL: {url}
- Score: {score}/10
- Reason: {reason}
- Tags: {tags}

**Full Content:**
{content}
{comments_section}
**Engagement Signals:**
{engagement}

**Web Search Results (for grounding and context):**
{web_context}

**Available Sources:**
{sources}

Write the blog post now in {language_name}. Output raw Markdown only.""",
    ranking_context="",  # deprecated — scoring_dimensions used instead
    research_system="""You identify technical concepts in news that a reader might not know.
Given a news item, return 1-3 search queries for concepts that need explanation.
Focus on: specific technologies, protocols, algorithms, tools, or projects that are not widely known.
Do NOT return queries for well-known things (e.g. "Python", "Linux", "Google").
If the news is self-explanatory, return an empty list.""",
    research_user="""What concepts in this news might need explanation?

Title: {title}
Summary: {summary}
Tags: {tags}
Content: {content}

Keep each query short (under 8 words).

Return plain natural language queries only — no boolean operators (OR, AND, NOT), no quoted phrases.

Respond with valid JSON only:
{{
  "queries": ["<search query 1>", "<search query 2>"]
}}""",
)
