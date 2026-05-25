## Context

The practitioner profile in `src/blog/profiles/practitioner.py` defines four `ScoringDimension` objects and two `gate_paths`. Real runs revealed two failure modes:

1. **Path A too permissive**: `technical_substance >= 5` lets in business deals with technical framing (OpenAI+Dell scored 7 on technical_substance). The anchor for 5 ("technical blog or API docs with some concrete specifics") is too broad.
2. **Path B structurally flawed**: `ai_ecosystem_significance` as a gate is both too narrow (only captures major providers) and calibration-unstable (secondary journalism about Google I/O scores 7-8 because the model conflates the significance of the underlying event with the quality of the item).
3. **Research papers excluded**: `production_applicability` on every path means papers that are not yet deployable fail both gates even when they have high engineering relevance and technical depth.

## Goals / Non-Goals

**Goals:**
- Path A captures research papers, benchmarks, and novel techniques regardless of deployability.
- Path B captures deployable models, APIs, libraries, and tools — including model releases that lack papers.
- Business deals and secondary journalism reliably fail both paths.
- No code changes outside `src/blog/profiles/practitioner.py`.

**Non-Goals:**
- Changes to the journalist profile.
- Changes to the scoring infrastructure (`runner.py`, `models.py`, `prompts.py`).
- Making `ai_ecosystem_significance` a gate for any path.

## Decisions

### 1. New gate_paths structure

```python
gate_paths = [
    ["ml_engineering_relevance", "technical_substance"],             # Path A: Research
    ["ml_engineering_relevance", "technical_substance", "production_applicability"],  # Path B: Deployable
]
```

Path A has no `production_applicability` gate. Path B has all three. Both paths share `ml_engineering_relevance` and `technical_substance` gates but at different thresholds (7 vs 6).

**Alternative considered**: Single path with a lower `production_applicability` threshold (>= 3). Rejected — too permissive; a paper with score 3 on applicability ("theoretical, years away") should still pass, but a business deal with score 4 should not. Having no gate on applicability for Path A is cleaner than a very low threshold.

### 2. Revised `technical_substance` definition and anchors

New description: "Is there a concrete technical artifact — a deployable model, open-source repo, paper with methodology, benchmark, or working API?"

```
1  — Business/PR announcement, no technical artifact of any kind
5  — Model announced but not yet available, OR technical blog with some concrete specifics
7  — Working model accessible via API/download with model card,
     OR paper with real implementation details and reproducible results
9  — Open-weights model with full technical report,
     OR paper + code + benchmark methodology
10 — Full paper + open-source code + benchmark + ablations + model weights
```

This moves model releases (GPT-5 API, Llama 4 weights) to 7-9, and moves partnership announcements without artifacts (OpenAI+Dell) to 2-3.

**Why not just raise the threshold to 6 or 7 with the old definition?** The old description excluded models as artifacts, so model releases would still score low. Redefining the dimension is necessary.

### 3. `ai_ecosystem_significance` demoted to ranking-only

Removed from `gate_paths`. Stays in `scoring_dimensions` with its current definition and anchors. Contributes to the Path B weighted sum (`path_b_weight = 0.15`) to rank key-provider releases above smaller model releases within included items.

The Path B weighted sum becomes:
```
ml_engineering_relevance × 0.35 + technical_substance × 0.30
+ production_applicability × 0.20 + ai_ecosystem_significance × 0.15
```

Path A weighted sum (no production_applicability or ecosystem dimension in the gate):
```
ml_engineering_relevance × 0.55 + technical_substance × 0.45
```

### 4. Threshold changes

| Dimension | Old Path A gate | New Path A gate | Old Path B gate | New Path B gate |
|---|---|---|---|---|
| ml_engineering_relevance | 6 | 7 | — | 6 |
| technical_substance | 5 | 7 | — | 6 |
| production_applicability | 4 | (none) | 5 | 6 |
| ai_ecosystem_significance | — | (none) | 7 | (none — ranking only) |

## Risks / Trade-offs

- **Path A may over-include theoretical research**: With no `production_applicability` gate, a mathematics paper that mentions ML tangentially could pass if it scores 7+ on both dimensions. Mitigated by `ml_engineering_relevance >= 7` — a maths paper without direct ML engineering relevance should score 4-5.
- **Path B threshold for `technical_substance` at 6**: Borderline items (business deals with some API details) may score 6. The revised anchors push these to 3-5, so calibration depends on prompt quality. → Monitor in run logs; raise to 7 if needed.
- **Weighted sum weights changed**: Path A no longer includes `production_applicability` or `ai_ecosystem_significance` in its sum. Research papers ranked by Path A weighted sum will be compared correctly within that cohort.

## Open Questions

- Should Path A `ml_engineering_relevance` gate be 7 or 8? 7 is chosen as a starting point — 8 might be too strict for good-but-not-paradigm-shifting papers.
- After running against a 1-week news window, are the Path A thresholds correctly calibrated? The design anticipates threshold tuning.
