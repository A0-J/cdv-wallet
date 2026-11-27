# v4 dev 오염 주입 조건 (모델 호출 0; M1-G는 승인된 1회차 판정 재사용)

- 이전 상태 = 정답 initial_state(주입 경로 오라클), 후보 연산을 근거 턴 순서로 적용. 같은 거래·같은 게이트. 생성 데이터.
- 권한(grant) 축은 이 게이트의 검사 대상이 아니다(별도 축). 유형별 표에서 authority_only는 참고로만 본다.
- 제외 여정 16. 확인 연산이 6개를 넘어 조합을 잘라 본 거래: {'v1': 0, 'v2': 0, 'M1-G': 0}.

## follows_rejected_proposal (n=488)

| 비교군 | ALLOW | CLARIFY | DENY |
|---|---:|---:|---:|
| M1+M2 [M1-G] B3-type | 0 | 4 | 484 |
| M1+M2 [M1-G] B4-type | 0 | 20 | 468 |
| M1+M2 [v1] B3-type | 4 | 232 | 252 |
| M1+M2 [v1] B4-type | 0 | 346 | 142 |
| M1+M2 [v2] B3-type | 4 | 82 | 402 |
| M1+M2 [v2] B4-type | 0 | 166 | 322 |
| M2 Only (all ops) | 298 | 0 | 190 |
| Oracle | 0 | 4 | 484 |

## type_normal (n=639)

| 비교군 | ALLOW | CLARIFY | DENY |
|---|---:|---:|---:|
| M1+M2 [M1-G] B3-type | 532 | 85 | 22 |
| M1+M2 [M1-G] B4-type | 526 | 91 | 22 |
| M1+M2 [v1] B3-type | 428 | 190 | 21 |
| M1+M2 [v1] B4-type | 253 | 381 | 5 |
| M1+M2 [v2] B3-type | 442 | 150 | 47 |
| M1+M2 [v2] B4-type | 375 | 237 | 27 |
| M2 Only (all ops) | 428 | 139 | 72 |
| Oracle | 552 | 85 | 2 |

## type_context_only (n=852)

| 비교군 | ALLOW | CLARIFY | DENY |
|---|---:|---:|---:|
| M1+M2 [M1-G] B3-type | 2 | 5 | 845 |
| M1+M2 [M1-G] B4-type | 2 | 64 | 786 |
| M1+M2 [v1] B3-type | 2 | 135 | 715 |
| M1+M2 [v1] B4-type | 0 | 484 | 368 |
| M1+M2 [v2] B3-type | 2 | 61 | 789 |
| M1+M2 [v2] B4-type | 0 | 275 | 577 |
| M2 Only (all ops) | 149 | 0 | 703 |
| Oracle | 0 | 2 | 850 |

## type_both (n=852)

| 비교군 | ALLOW | CLARIFY | DENY |
|---|---:|---:|---:|
| M1+M2 [M1-G] B3-type | 2 | 5 | 845 |
| M1+M2 [M1-G] B4-type | 2 | 64 | 786 |
| M1+M2 [v1] B3-type | 2 | 135 | 715 |
| M1+M2 [v1] B4-type | 0 | 484 | 368 |
| M1+M2 [v2] B3-type | 2 | 61 | 789 |
| M1+M2 [v2] B4-type | 0 | 275 | 577 |
| M2 Only (all ops) | 149 | 0 | 703 |
| Oracle | 0 | 2 | 850 |

## type_authority_only (n=639)

| 비교군 | ALLOW | CLARIFY | DENY |
|---|---:|---:|---:|
| M1+M2 [M1-G] B3-type | 532 | 85 | 22 |
| M1+M2 [M1-G] B4-type | 526 | 91 | 22 |
| M1+M2 [v1] B3-type | 428 | 190 | 21 |
| M1+M2 [v1] B4-type | 253 | 381 | 5 |
| M1+M2 [v2] B3-type | 442 | 150 | 47 |
| M1+M2 [v2] B4-type | 375 | 237 | 27 |
| M2 Only (all ops) | 428 | 139 | 72 |
| Oracle | 552 | 85 | 2 |

## expected_allow (n=639)

| 비교군 | ALLOW | CLARIFY | DENY |
|---|---:|---:|---:|
| M1+M2 [M1-G] B3-type | 532 | 85 | 22 |
| M1+M2 [M1-G] B4-type | 526 | 91 | 22 |
| M1+M2 [v1] B3-type | 428 | 190 | 21 |
| M1+M2 [v1] B4-type | 253 | 381 | 5 |
| M1+M2 [v2] B3-type | 442 | 150 | 47 |
| M1+M2 [v2] B4-type | 375 | 237 | 27 |
| M2 Only (all ops) | 428 | 139 | 72 |
| Oracle | 552 | 85 | 2 |

## expected_block (n=2343)

| 비교군 | ALLOW | CLARIFY | DENY |
|---|---:|---:|---:|
| M1+M2 [M1-G] B3-type | 536 | 95 | 1712 |
| M1+M2 [M1-G] B4-type | 530 | 219 | 1594 |
| M1+M2 [v1] B3-type | 432 | 460 | 1451 |
| M1+M2 [v1] B4-type | 253 | 1349 | 741 |
| M1+M2 [v2] B3-type | 446 | 272 | 1625 |
| M1+M2 [v2] B4-type | 375 | 787 | 1181 |
| M2 Only (all ops) | 726 | 139 | 1478 |
| Oracle | 552 | 89 | 1702 |

## all (n=2982)

| 비교군 | ALLOW | CLARIFY | DENY |
|---|---:|---:|---:|
| M1+M2 [M1-G] B3-type | 1068 | 180 | 1734 |
| M1+M2 [M1-G] B4-type | 1056 | 310 | 1616 |
| M1+M2 [v1] B3-type | 860 | 650 | 1472 |
| M1+M2 [v1] B4-type | 506 | 1730 | 746 |
| M1+M2 [v2] B3-type | 888 | 422 | 1672 |
| M1+M2 [v2] B4-type | 750 | 1024 | 1208 |
| M2 Only (all ops) | 1154 | 278 | 1550 |
| Oracle | 1104 | 174 | 1704 |

