## 1. Revise technical_substance dimension

- [x] 1.1 Update `technical_substance` description to "Is there a concrete technical artifact — a deployable model, open-source repo, paper with methodology, benchmark, or working API?"
- [x] 1.2 Replace `technical_substance` anchors with: 1=no artifact, 5=model announced but not available OR technical blog, 7=working model via API/download + model card OR paper with real implementation details, 9=open-weights model + technical report OR paper + code + benchmarks, 10=full paper + code + benchmark + ablations + model weights
- [x] 1.3 Set `technical_substance.gate_threshold` to 7.0 (was 5.0; Path A gate will be >= 7)

## 2. Revise ml_engineering_relevance dimension

- [x] 2.1 Set `ml_engineering_relevance.gate_threshold` to 7.0 (was 6.0; Path A gate will be >= 7)
- [x] 2.2 Update `ml_engineering_relevance` path_a_weight to 0.55 (was 0.45) and path_b_weight to 0.35 (was 0.0)

## 3. Revise technical_substance weights

- [x] 3.1 Update `technical_substance.path_a_weight` to 0.45 (was 0.35) and `path_b_weight` to 0.30 (was 0.0)

## 4. Revise production_applicability dimension

- [x] 4.1 Set `production_applicability.gate_threshold` to 6.0 (was 5.0; Path B gate will be >= 6)
- [x] 4.2 Update `production_applicability.path_a_weight` to 0.0 (was 0.20; not used in Path A) and `path_b_weight` to 0.20 (was 0.40)

## 5. Demote ai_ecosystem_significance to ranking-only

- [x] 5.1 Update `ai_ecosystem_significance.path_b_weight` to 0.15 (was 0.60; ranking contribution only)
- [x] 5.2 Set `ai_ecosystem_significance.gate_threshold` to any value (irrelevant; dimension no longer in any gate path — set to 7.0 as documentation)

## 6. Redesign gate_paths

- [x] 6.1 Replace `gate_paths` with: `[["ml_engineering_relevance", "technical_substance"], ["ml_engineering_relevance", "technical_substance", "production_applicability"]]`
- [x] 6.2 Verify `ai_ecosystem_significance` is absent from all gate paths

## 7. Verify runner compatibility

- [x] 7.1 Confirm that `runner.py`'s `_compute_weighted_sum` handles dimensions with weight 0 for a given path (they already do — path_a_weight=0 or path_b_weight=0 simply contributes 0 to the sum)
- [x] 7.2 Confirm that `score_items_for_profile` still evaluates all 4 dimensions regardless of gate_paths (scoring is independent of gate membership)
