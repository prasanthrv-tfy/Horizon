# Blog Profiles

Reference for the scoring profiles used by `horizon-blog`. Each profile defines the audience, gate path logic, scoring dimensions, and score milestones that determine which items are selected and ranked.

Update this file when profile code in `src/blog/profiles/` changes.

---

## News Profile

**Audience:** General tech readers — people who follow tech news but are not necessarily practitioners.  
**Purpose:** Selects and ranks items for their broad significance, newsworthiness, and accessibility to a non-expert audience.

### Gate path

A single path (`news_stories`); items must clear all three dimensions:

> **news_stories:** significance ≥ 6  AND  newsworthiness ≥ 5  AND  narrative_clarity ≥ 4

### Scoring dimensions & weights

| Dimension | Description | Gate | Weight |
|---|---|---|---|
| `significance` | How broadly significant is this development for the AI/tech landscape? | ≥ 6 | 0.45 |
| `newsworthiness` | Is this timely, original, and a primary announcement rather than derivative commentary? | ≥ 5 | 0.35 |
| `narrative_clarity` | Is there a clear, compelling story a non-expert reader can follow? | ≥ 4 | 0.20 |

**Weighted sum:** `0.45 × significance + 0.35 × newsworthiness + 0.20 × narrative_clarity`

### Score milestones

**`significance`** — gate ≥ 6

| Score | Meaning |
|---|---|
| 1 | Niche announcement affecting a tiny audience |
| 5 | Noteworthy for a specific community but limited broader impact |
| **6 (gate)** | Broadly relevant — affects AI/tech users or the industry in a tangible way |
| 8 | Affects many users, products, or industries in a meaningful way |
| 10 | Industry-defining event — affects everyone in the tech ecosystem |

**`newsworthiness`** — gate ≥ 5

| Score | Meaning |
|---|---|
| 1 | Old news resurfacing or pure opinion with no new facts |
| **5 (gate)** | Secondary coverage of a genuine event with some new angle |
| 8 | Primary announcement, breaking news, or original reporting |
| 10 | Major breaking development from the primary source, first of its kind |

**`narrative_clarity`** — gate ≥ 4 *(rarely binding in practice)*

| Score | Meaning |
|---|---|
| 1 | Highly technical or jargon-heavy with no accessible angle |
| 5 | Story exists but requires significant background to appreciate |
| 8 | Clear narrative with obvious stakes a general reader would understand |
| 10 | Compelling human or societal story that writes itself for any audience |

---

## Engineer Profile

**Audience:** ML/MLOps engineers — people who build, fine-tune, serve, and evaluate models in production.  
**Purpose:** Selects items based on ML engineering relevance and technical substance. Two named gate paths let research-significant posts through alongside immediately deployable content.

### Gate paths

An item passes if it clears **all dimensions in any one path** (OR across paths, AND within a path):

| Path | Purpose | Gate conditions |
|---|---|---|
| **`engineering_applicability`** | Ready-to-adopt tools, APIs, model releases, and production guides | ml_engineering_relevance ≥ 7 AND technical_substance ≥ 5 AND production_applicability ≥ 6 AND ai_ecosystem_significance ≥ 7 |
| **`technical_insights`** | Research with important engineering insights, even if not yet deployable | ml_engineering_relevance ≥ 8 AND technical_substance ≥ 5 AND engineering_insight ≥ 6 |

When an item passes both paths, `engineering_applicability` is used (first match) and its weighted sum is applied.

### Scoring dimensions & weights

| Dimension | Description | engineering_applicability gate | engineering_applicability weight | technical_insights gate | technical_insights weight |
|---|---|---|---|---|---|
| `ml_engineering_relevance` | Relevance to building, fine-tuning, serving, or evaluating ML models in production | ≥ 7 | 0.35 | ≥ 8 | 0.45 |
| `technical_substance` | Concrete technical detail an ML engineer can learn from | ≥ 5 | 0.30 | ≥ 5 | 0.30 |
| `production_applicability` | Can be adopted in an ML stack this sprint | ≥ 6 | 0.20 | — | — |
| `ai_ecosystem_significance` | Major model/API release from a key provider vs. niche | ≥ 7 | 0.15 | — | — |
| `engineering_insight` | Advances understanding of how to design, build, or operate ML systems | — | — | ≥ 6 | 0.25 |

**Weighted sums:**
- `engineering_applicability`: `0.35 × ml_engineering_relevance + 0.30 × technical_substance + 0.20 × production_applicability + 0.15 × ai_ecosystem_significance`
- `technical_insights`: `0.45 × ml_engineering_relevance + 0.30 × technical_substance + 0.25 × engineering_insight`

### Score milestones

**`ml_engineering_relevance`** — gate ≥ 7 (engineering_applicability) / ≥ 8 (technical_insights)

| Score | Meaning |
|---|---|
| 1 | No ML engineering content — business, policy, or consumer product news |
| 5 | Tangentially ML-related (platform news, infra update with minor ML angle) |
| **7 (engineering_applicability gate)** | Relevant to ML engineering — about a tool, technique, or result engineers work with |
| **8 (technical_insights gate)** | Directly about a technique, tool, or result engineers should act on |
| 10 | Paradigm shift in how models are trained, served, or evaluated |

**`technical_substance`** — gate ≥ 5 (both paths)

| Score | Meaning |
|---|---|
| 1 | Pure business/PR with no technical details — partnership deal, funding round, executive hire |
| 4 | Vague capability claims with no supporting numbers, architecture details, or methodology; OR feature announced with no technical specifics and no confirmed availability |
| **5 (gate — both paths)** | Research or lab blog post that describes a method or finding at a conceptual level — some methodology described, but key implementation details or reproducible numbers are not provided |
| 6 | Technically rich content an ML engineer can learn from: new open or API-accessible model with architecture details, efficiency numbers, or benchmark results; OR working SDK/API with technical docs; OR engineering blog with concrete implementation details; OR research algorithm with experimental results |
| 7 | Deployed model with model card and benchmark results; OR paper with clear methodology, concrete experiments, and reproducible numbers |
| 9 | Open-weights model with full technical report and benchmark suite, OR paper + code + benchmark methodology |
| 10 | Full paper + open-source code + benchmark + ablations + model weights |

**`production_applicability`** — gate ≥ 6 (engineering_applicability only)

| Score | Meaning |
|---|---|
| 1 | Theoretical or hypothetical — years from being usable |
| 5 | Limited/beta access or requires significant custom work |
| **6 (gate)** | Accessible with moderate effort — integration path exists but needs custom work |
| 8 | Available with straightforward setup, clear integration path |
| 10 | Available now, works out of the box, engineers can adopt immediately |

**`ai_ecosystem_significance`** — gate ≥ 7 (engineering_applicability only)

| Score | Meaning |
|---|---|
| 1 | Internal tooling or niche product with limited audience |
| 5 | Minor model variant or incremental version bump |
| **7 (gate)** | Meaningful release from a key provider that practitioners would evaluate for deployment |
| 8 | Primary announcement of a significant model update or major new capability from a key provider |
| 10 | Flagship model release (GPT-5, Claude 4, Llama 4, Gemini 2) or paradigm-shifting product change |

**`engineering_insight`** — gate ≥ 6 (technical_insights only)

| Score | Meaning |
|---|---|
| 1 | No engineering insight — pure business news, market commentary, or consumer product update |
| 4 | Broadly interesting to ML people but does not advance engineering knowledge |
| **6 (gate)** | Directly informs how practitioners should think about designing, evaluating, or operating ML systems |
| 8 | Hands-on research with clear engineering implications practitioners should incorporate into their workflow |
| 10 | Paradigm-shifting engineering insight with validated results that changes how ML systems should be built |
