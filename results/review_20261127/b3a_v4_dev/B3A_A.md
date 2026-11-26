# B3-A(비대칭 기각, 보조 구성, Holm 대상 아님) — v4 dev 조건 A, 모델 호출 0

- M1-G 응답은 `ledger_m1g_v4.jsonl` 재생. 원장에 없는 요청 때문에 계산하지 못한 거래 0(보내지 않음), 재생 적중 19186, 미스 0.
- 저장된 B3 대 재생한 B3 판정 일치 1445/1474 (원장에 같은 요청의 답이 여럿이면 재생은 하나만 쓴다).

| 유형 (n) | B2 | B3 | B3_replay | B3-A | PRECHECK |
|---|---|---|---|---|---|
| normal (307) | 286/13/8 | 246/52/9 | 245/52/10 | 245/52/10 | 201/100/6 |
| context_only (430) | 9/4/417 | 60/34/336 | 64/33/333 | 17/80/333 | 0/9/421 |
| both (430) | 9/4/417 | 63/32/335 | 64/33/333 | 17/80/333 | 1/4/425 |
| authority_only (307) | 286/13/8 | 245/52/10 | 245/52/10 | 245/52/10 | 197/103/7 |

## 거짓 전제 동의 (매칭 사례 4, n=16, 기준 판정 CLARIFY; DENY는 정답 아님)

| 구성 | ALLOW | CLARIFY | DENY |
|---|---:|---:|---:|
| B2 | 1 | 3 | 12 |
| B3 | 1 | 4 | 11 |
| B3_replay | 1 | 4 | 11 |
| B3-A | 1 | 4 | 11 |
| PRECHECK | 13 | 3 | 0 |

## B3가 B2보다 정상 거래를 덜 허용한 거래 (B2 ALLOW, B3 아님): 42건

- B3_replay 판정·원인: CLARIFY: 선택 불일치, 선택 상품 포함 9, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [OMISSION] 5, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [OMISSION,SELECTION_UNRESOLVED] 5, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [M1G_AMBIGUOUS,OMISSION,SELECTION_UNRESOLVED] 4, CLARIFY: M1 확인 [OMISSION] 4, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [M1G_AMBIGUOUS,SELECTION_UNRESOLVED] 3, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [SELECTION_UNRESOLVED] 2, CLARIFY: M1 확인 [M1G_AMBIGUOUS,SELECTION_UNRESOLVED] 2, CLARIFY: M1 확인 [M1G_AMBIGUOUS] 1, DENY: 수량 1, CLARIFY: 정보 부족(확인), M1 확인 [OMISSION] 1, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [M1G_AMBIGUOUS,OMISSION] 1, CLARIFY: 선택 불일치, 수량 1, DENY: 브랜드 1, CLARIFY: 정보 부족(확인) 1, DENY: 묶음 구성 1

## B3-A가 B2보다 정상 거래를 덜 허용한 거래: 42건

- B3-A 판정·원인: CLARIFY: 선택 불일치, 선택 상품 포함 9, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [OMISSION] 4, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [M1G_AMBIGUOUS,OMISSION,SELECTION_UNRESOLVED] 4, CLARIFY: M1 확인 [OMISSION] 4, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [OMISSION,SELECTION_UNRESOLVED] 4, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [M1G_AMBIGUOUS,SELECTION_UNRESOLVED] 2, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [SELECTION_UNRESOLVED] 2, CLARIFY: M1 확인 [M1G_AMBIGUOUS,SELECTION_UNRESOLVED] 2, CLARIFY: M1 확인 [M1G_AMBIGUOUS,M1G_REJECT_NARROWING] 1, DENY: 수량 1, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [M1G_AMBIGUOUS,M1G_REJECT_NARROWING,SELECTION_UNRESOLVED] 1, CLARIFY: 정보 부족(확인), M1 확인 [OMISSION] 1, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [M1G_AMBIGUOUS,OMISSION] 1, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [M1G_REJECT_NARROWING,OMISSION,SELECTION_UNRESOLVED] 1, CLARIFY: 선택 불일치, 수량 1, DENY: 브랜드 1, CLARIFY: 정보 부족(확인) 1, DENY: 묶음 구성 1, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [M1G_REJECT_NARROWING,OMISSION] 1

## B3가 B2보다 위반 거래를 더 허용한 거래 (B2 차단, B3 ALLOW): 56건

- 정답 위반 필드: Deadline 43, Quantity 10, Fulfillment 3
- B2 차단 사유: DEADLINE 43, QUANTITY 9, FULFILLMENT 3, BRAND 1
- M1 기각 코드(B3): M1G_not_mentioned 86, M1G_question 6

## B3-A가 B2보다 위반 거래를 더 허용한 거래: 9건

- 정답 위반 필드: Quantity 9
- B2 차단 사유: QUANTITY 9
- M1 기각 코드(B3): M1G_not_mentioned 10
