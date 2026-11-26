# G1 평가 세트 재집계: 중복 제거 + X1 제외 (2026-11-26)

- 규칙: 대화가 같은 사례는 첫 사례만 남김(6묶음 → 6사례 제거), X1_two_budgets_unresolved 전부 제외(충돌이 대화에 없어 평가되지 않았음, `G1_DUPLICATES.md`). 행 파일: `rows_G1_eval_dedup_noX1.jsonl`. 원 행 파일은 그대로다.
- 남은 사례: 234 (원 260)

| 비교군 | 원(260) | 중복 제거(254) | 중복 제거 + X1 제외 |
|---|---|---|---|
| plain | 222/260 = 85.4% | 217/254 = 85.4% | 197/234 = 84.2% |
| fnctod | 227/260 = 87.3% | 222/254 = 87.4% | 202/234 = 86.3% |
| fnctod_r | 246/260 = 94.6% | 240/254 = 94.5% | 220/234 = 94.0% |
| fnctod_rn | 250/260 = 96.2% | 244/254 = 96.1% | 224/234 = 95.7% |

## 템플릿별 (중복 제거 + X1 제외)

| 템플릿 | n | plain | fnctod | fnctod_r | fnctod_rn |
|---|---:|---:|---:|---:|---:|
| C1_relax_explicit | 20 | 20 | 20 | 20 | 20 |
| C2_relax_no_cue | 20 | 20 | 20 | 18 | 20 |
| C3_relax_seller_source | 20 | 20 | 20 | 18 | 18 |
| C4_relax_value_mismatch | 20 | 20 | 20 | 20 | 20 |
| C5_tighten | 19 | 19 | 19 | 19 | 19 |
| C6_ambiguous_pick_bundle | 18 | 10 | 13 | 18 | 18 |
| C7_explicit_drop_bundle | 20 | 13 | 13 | 13 | 13 |
| C8_add_substitute | 20 | 18 | 20 | 20 | 20 |
| C9_substitute_no_cue | 20 | 20 | 20 | 18 | 19 |
| O1_omitted_budget | 19 | 19 | 19 | 19 | 19 |
| X2_budget_overridden | 18 | 18 | 18 | 18 | 18 |
| X3_brand_in_out | 20 | 0 | 0 | 19 | 20 |
