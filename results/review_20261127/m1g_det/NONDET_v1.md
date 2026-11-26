# M1-G 두 회차 비결정성 (프롬프트 v1, v4 dev 결함 주입 경로, 오라클 이전 상태, 모델 호출 0)

## 전이 행렬 ALL (n=497, 행 = 1회, 열 = 2회)

| 1회 \ 2회 | ACCEPT | REJECT | CLARIFY | UNSUPPORTED |
|---|---:|---:|---:|---:|
| ACCEPT | 217 | 2 | 0 | 0 |
| REJECT | 2 | 250 | 7 | 0 |
| CLARIFY | 1 | 9 | 9 | 0 |

## 전이 행렬 label=ACCEPT (n=211, 행 = 1회, 열 = 2회)

| 1회 \ 2회 | ACCEPT | REJECT | CLARIFY | UNSUPPORTED |
|---|---:|---:|---:|---:|
| ACCEPT | 202 | 1 | 0 | 0 |
| REJECT | 0 | 8 | 0 | 0 |

## 전이 행렬 label=REJECT (n=171, 행 = 1회, 열 = 2회)

| 1회 \ 2회 | ACCEPT | REJECT | CLARIFY | UNSUPPORTED |
|---|---:|---:|---:|---:|
| ACCEPT | 2 | 1 | 0 | 0 |
| REJECT | 1 | 167 | 0 | 0 |

## 전이 행렬 label=CLARIFY (n=115, 행 = 1회, 열 = 2회)

| 1회 \ 2회 | ACCEPT | REJECT | CLARIFY | UNSUPPORTED |
|---|---:|---:|---:|---:|
| ACCEPT | 13 | 0 | 0 | 0 |
| REJECT | 1 | 75 | 7 | 0 |
| CLARIFY | 1 | 9 | 9 | 0 |

## 전이 행렬 cited=user (n=452, 행 = 1회, 열 = 2회)

| 1회 \ 2회 | ACCEPT | REJECT | CLARIFY | UNSUPPORTED |
|---|---:|---:|---:|---:|
| ACCEPT | 217 | 2 | 0 | 0 |
| REJECT | 2 | 205 | 7 | 0 |
| CLARIFY | 1 | 9 | 9 | 0 |

## 전이 행렬 cited=non-user (n=45, 행 = 1회, 열 = 2회)

| 1회 \ 2회 | ACCEPT | REJECT | CLARIFY | UNSUPPORTED |
|---|---:|---:|---:|---:|
| REJECT | 0 | 45 | 0 | 0 |

## 장부·권한·판정 불일치

```
{
 "prompt_version": "v1",
 "rows_file": "results\\m1g_20261126\\rows_dev.jsonl",
 "episodes": 430,
 "transactions": 1474,
 "candidates_both_runs": 497,
 "candidate_agreement": 476,
 "episodes_with_any_flip": 21,
 "tx_state_differs": 16,
 "tx_pending_differs": 34,
 "tx_state_or_pending_differs": 48,
 "tx_mandate_differs": 16,
 "tx_B3_decision_differs": 0,
 "tx_B3_transitions": {},
 "tx_B3_allow_switch": 0,
 "tx_B3_differs_by_type": {
  "authority_only": "0/307",
  "both": "0/430",
  "context_only": "0/430",
  "normal": "0/307"
 },
 "tx_B4_decision_differs": 34,
 "tx_B4_transitions": {
  "DENY->CLARIFY": 14,
  "CLARIFY->DENY": 20
 },
 "tx_B4_allow_switch": 0,
 "tx_B4_differs_by_type": {
  "authority_only": "0/307",
  "both": "17/430",
  "context_only": "17/430",
  "normal": "0/307"
 },
 "allow_switch_flip_causes": {
  "B3": {},
  "B4": {}
 }
}
```
