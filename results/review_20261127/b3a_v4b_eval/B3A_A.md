# B3-A(비대칭 기각, 보조 구성, Holm 대상 아님) — v4b eval 조건 A, 모델 호출 0

- M1-G 응답은 `ledger_m1g_v4b.jsonl` 재생. 원장에 없는 요청 때문에 계산하지 못한 거래 0(보내지 않음), 재생 적중 38200, 미스 0.
- 저장된 B3 대 재생한 B3 판정 일치 2982/2982 (원장에 같은 요청의 답이 여럿이면 재생은 하나만 쓴다).

| 유형 (n) | B2 | B3 | B3_replay | B3-A | PRECHECK |
|---|---|---|---|---|---|
| normal (639) | 592/21/26 | 519/100/20 | 519/100/20 | 519/100/20 | 406/221/12 |
| context_only (852) | 32/3/817 | 121/18/713 | 121/18/713 | 52/87/713 | 1/12/839 |
| both (852) | 32/3/817 | 121/18/713 | 121/18/713 | 52/87/713 | 2/14/836 |
| authority_only (639) | 592/21/26 | 519/100/20 | 519/100/20 | 519/100/20 | 397/225/17 |

## 거짓 전제 동의 (매칭 사례 4, n=33, 기준 판정 CLARIFY; DENY는 정답 아님)

| 구성 | ALLOW | CLARIFY | DENY |
|---|---:|---:|---:|
| B2 | 2 | 0 | 31 |
| B3 | 4 | 2 | 27 |
| B3_replay | 4 | 2 | 27 |
| B3-A | 2 | 4 | 27 |
| PRECHECK | 10 | 23 | 0 |

## B3가 B2보다 정상 거래를 덜 허용한 거래 (B2 ALLOW, B3 아님): 74건

- B3_replay 판정·원인: CLARIFY: 선택 불일치, 선택 상품 포함 39, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [SELECTION_UNRESOLVED] 16, CLARIFY: 정보 부족(확인) 14, CLARIFY: M1 확인 [M1G_AMBIGUOUS] 2, CLARIFY: 선택 불일치, 수량 1, CLARIFY: 수량, M1 확인 [M1G_AMBIGUOUS,SELECTION_UNRESOLVED] 1, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [M1G_AMBIGUOUS,SELECTION_UNRESOLVED] 1

## B3-A가 B2보다 정상 거래를 덜 허용한 거래: 74건

- B3-A 판정·원인: CLARIFY: 선택 불일치, 선택 상품 포함 39, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [SELECTION_UNRESOLVED] 14, CLARIFY: 정보 부족(확인) 14, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [M1G_REJECT_NARROWING,SELECTION_UNRESOLVED] 2, CLARIFY: M1 확인 [M1G_AMBIGUOUS,M1G_REJECT_NARROWING] 1, CLARIFY: 선택 불일치, 수량 1, CLARIFY: M1 확인 [M1G_AMBIGUOUS] 1, CLARIFY: 수량, M1 확인 [M1G_AMBIGUOUS,SELECTION_UNRESOLVED] 1, CLARIFY: 선택 불일치, 선택 상품 포함, M1 확인 [M1G_AMBIGUOUS,SELECTION_UNRESOLVED] 1

## B3가 B2보다 위반 거래를 더 허용한 거래 (B2 차단, B3 ALLOW): 90건

- 정답 위반 필드: Deadline 50, Quantity 21, Fulfillment 18, Price 1
- B2 차단 사유: DEADLINE 49, QUANTITY 21, FULFILLMENT 17, BRAND 2, MAX_TOTAL_WITH_FEES 1
- M1 기각 코드(B3): M1G_not_mentioned 155, M1G_question 7

## B3-A가 B2보다 위반 거래를 더 허용한 거래: 21건

- 정답 위반 필드: Quantity 21
- B2 차단 사유: QUANTITY 21
- M1 기각 코드(B3): M1G_not_mentioned 27, M1G_question 1
