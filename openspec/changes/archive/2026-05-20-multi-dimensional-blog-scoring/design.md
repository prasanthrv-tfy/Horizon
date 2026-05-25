## Context

`src/blog/runner.py` currently calls `rank_by_relevance()` inside the profile loop, which asks the LLM to return a sorted list of item IDs. There are no scores, no reasons, and no filter — the top `max_posts` items always get posts. The previous change (`profile-aware-blog-ranking`) made this profile-aware, but a ranked order without a relevance bar still produces posts for irrelevant items when the entire pool is low quality.

The target audience is TrueFoundry's users: ML engineers who deploy, serve, and fine-tune models in production. They need a scoring system that can distinguish "new vLLM speculative decoding improvement with benchmark" from "OpenAI and Dell sign enterprise deal."

## Goals / Non-Goals

**Goals:**
- Score every candidate item on 4 named dimensions, each with a 0-10 score and a reason.
- Apply gate logic per profile (two OR paths for practitioner) to include/exclude items.
- Compute a per-path weighted sum that fairly ranks both "technical depth" items and "ecosystem event" items.
- Emit a JSON run log and rich console output so operators can trace every decision.
- Allow zero posts when nothing passes the gates.

**Non-Goals:**
- Making the upstream pipeline scorer (`CONTENT_ANALYSIS_SYSTEM`) profile-aware — separate future work.
- Caching dimension scores across profiles (call 1 remains per-profile for simplicity).
- UI or API for browsing run logs.

## Decisions

### 1. Single LLM call scores all dimensions at once

All four dimensions, their scores, and their reasons are returned in one structured JSON response per profile run. This avoids one call per dimension (4×) or one call per item (N×).

**Alternative considered**: Two-call design — one call to characterise items (profile-agnostic), one to filter (profile-specific). Rejected for now: adds latency and complexity; the pool size (4–20 items) makes a single batched call cheap. Revisit when running across profiles concurrently.

### 2. Per-path weighted sum, not global weights

Two inclusion paths exist for the practitioner profile:
- **Path A** (technical depth): `ml_engineering_relevance × 0.45 + technical_substance × 0.35 + production_applicability × 0.20`
- **Path B** (ecosystem event): `ai_ecosystem_significance × 0.60 + production_applicability × 0.40`

`item.weighted_sum = max(path_a_sum, path_b_sum)`

**Why not global weights?** A model release (GPT-5, Llama 4) scores low on `technical_substance` (no paper) but high on `ai_ecosystem_significance`. Global weights biased toward Path A dimensions would systematically rank model releases below technical papers, causing them to be cut by `max_posts`. Per-path sums reflect what actually makes each item valuable under its inclusion path.

### 3. Gate paths expressed as lists of (dimension, threshold) pairs on the profile

```python
gate_paths: List[List[str]]
# e.g. [["ml_engineering_relevance", "technical_substance", "production_applicability"],
#        ["ai_ecosystem_significance", "production_applicability"]]
```

Each path is an AND of its dimensions against their thresholds. Include if ANY path passes (OR between paths). Thresholds live on the `ScoringDimension` object, not on the path, so each dimension has one canonical threshold regardless of which path references it.

**Alternative**: Express gate logic as a formula string (e.g. `"(A >= 6 AND B >= 5) OR (D >= 7)"`). Rejected — harder to parse reliably, adds a mini-language to maintain.

### 4. `ranking_context` deprecated, not removed

`BlogPromptProfile.ranking_context` is kept but ignored when `scoring_dimensions` is non-empty. This avoids a hard breaking change in case any external code references the field. Document as deprecated.

### 5. Run log schema

Written to `data/blog-runs/YYYY-MM-DD-{profile}.json`:

```json
{
  "profile": "practitioner",
  "run_at": "ISO-8601",
  "items_evaluated": 8,
  "items_included": 2,
  "items_excluded": 6,
  "results": [
    {
      "id": "...",
      "title": "...",
      "included": true,
      "inclusion_path": "A",
      "weighted_sum": 7.4,
      "dimensions": {
        "ml_engineering_relevance": {"score": 8, "reason": "..."},
        "technical_substance":      {"score": 7, "reason": "..."},
        "production_applicability": {"score": 8, "reason": "..."},
        "ai_ecosystem_significance": {"score": 5, "reason": "..."}
      },
      "path_results": {
        "A": {"passed": true,  "scores": {"ml_engineering_relevance": 8, ...}},
        "B": {"passed": false, "failed_gates": ["ai_ecosystem_significance"]}
      }
    }
  ]
}
```

### 6. Console output format

```
🔄 [practitioner] Scoring 8 items...

                                ml_rel  substance  apply  ecosystem  weighted  decision
  Databricks GPT-5.5              8        7         8        5        7.40    ✓ Path A
  EU AI licensing                 5        3         6        2        2.70    ✗
  OpenAI + Dell partnership       4        2         4        3        1.95    ✗
  Google I/O 2026 roundup         4        3         5        4        2.60    ✗
  Llama 4 release                 7        4         9        9        7.80    ✓ Path B

🏆 [practitioner] 2/8 items passed. Generating 2 posts.
```

## Risks / Trade-offs

- **LLM score calibration drift**: Scores are absolute (0–10) not relative. The same item may score differently across runs. → Anchors in the dimension description ground the scale; reasons make drift visible in logs.
- **Path B under-fires**: `ai_ecosystem_significance >= 7` is strict — only flagship model releases pass. Minor model updates (GPT-4o-mini variant) would fail. → Threshold is tunable; the 1-week test run will surface calibration issues.
- **Run log accumulation**: `data/blog-runs/` grows unbounded. → Gitignore the directory; operators can prune manually. Add retention policy later if needed.
- **Zero-post runs**: If no items pass, the blog runner exits cleanly with a log entry. → This is correct behavior but may surprise users running for the first time with a narrow window. Console message should be clear.

## Open Questions

- Should `data/blog-runs/` be gitignored globally or only locally? Suggest gitignore for now since logs may contain full item content.
- Should the journalist profile use a single gate path or two? Current design uses one path (significance AND newsworthiness AND narrative_clarity) — revisit after practitioner is validated.
