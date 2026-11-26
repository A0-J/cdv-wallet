# M1-G 두 회차 비결정성 (프롬프트 v2, v4 dev 결함 주입 경로, 오라클 이전 상태, 모델 호출 0)

## 전이 행렬 ALL (n=497, 행 = 1회, 열 = 2회)

| 1회 \ 2회 | ACCEPT | REJECT | CLARIFY | UNSUPPORTED |
|---|---:|---:|---:|---:|
| ACCEPT | 200 | 4 | 5 | 0 |
| REJECT | 2 | 220 | 10 | 0 |
| CLARIFY | 5 | 17 | 34 | 0 |

## 전이 행렬 label=ACCEPT (n=211, 행 = 1회, 열 = 2회)

| 1회 \ 2회 | ACCEPT | REJECT | CLARIFY | UNSUPPORTED |
|---|---:|---:|---:|---:|
| ACCEPT | 196 | 2 | 3 | 0 |
| REJECT | 2 | 3 | 0 | 0 |
| CLARIFY | 3 | 0 | 2 | 0 |

## 전이 행렬 label=REJECT (n=171, 행 = 1회, 열 = 2회)

| 1회 \ 2회 | ACCEPT | REJECT | CLARIFY | UNSUPPORTED |
|---|---:|---:|---:|---:|
| ACCEPT | 1 | 2 | 0 | 0 |
| REJECT | 0 | 168 | 0 | 0 |

## 전이 행렬 label=CLARIFY (n=115, 행 = 1회, 열 = 2회)

| 1회 \ 2회 | ACCEPT | REJECT | CLARIFY | UNSUPPORTED |
|---|---:|---:|---:|---:|
| ACCEPT | 3 | 0 | 2 | 0 |
| REJECT | 0 | 49 | 10 | 0 |
| CLARIFY | 2 | 17 | 32 | 0 |

## 전이 행렬 cited=user (n=452, 행 = 1회, 열 = 2회)

| 1회 \ 2회 | ACCEPT | REJECT | CLARIFY | UNSUPPORTED |
|---|---:|---:|---:|---:|
| ACCEPT | 200 | 4 | 5 | 0 |
| REJECT | 2 | 175 | 10 | 0 |
| CLARIFY | 5 | 17 | 34 | 0 |

## 전이 행렬 cited=non-user (n=45, 행 = 1회, 열 = 2회)

| 1회 \ 2회 | ACCEPT | REJECT | CLARIFY | UNSUPPORTED |
|---|---:|---:|---:|---:|
| REJECT | 0 | 45 | 0 | 0 |

## 장부·권한·판정 불일치

```
{
 "prompt_version": "v2",
 "rows_file": "results\\m1g_20261126\\prompt_v2\\rows_dev.jsonl",
 "episodes": 430,
 "transactions": 1474,
 "candidates_both_runs": 497,
 "candidate_agreement": 454,
 "episodes_with_any_flip": 41,
 "tx_state_differs": 38,
 "tx_pending_differs": 70,
 "tx_state_or_pending_differs": 88,
 "tx_mandate_differs": 28,
 "tx_B3_decision_differs": 0,
 "tx_B3_transitions": {},
 "tx_B3_allow_switch": 0,
 "tx_B3_differs_by_type": {
  "authority_only": "0/307",
  "both": "0/430",
  "context_only": "0/430",
  "normal": "0/307"
 },
 "tx_B4_decision_differs": 64,
 "tx_B4_transitions": {
  "CLARIFY->DENY": 38,
  "DENY->CLARIFY": 26
 },
 "tx_B4_allow_switch": 0,
 "tx_B4_differs_by_type": {
  "authority_only": "0/307",
  "both": "32/430",
  "context_only": "32/430",
  "normal": "0/307"
 },
 "allow_switch_flip_causes": {
  "B3": {},
  "B4": {}
 }
}
```
