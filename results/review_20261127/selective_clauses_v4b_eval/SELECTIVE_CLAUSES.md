# 선택적 재확인·조건부 조항·반복 일관성 (v4 dev 조건 A, 고정 코드 행 `m1g`, 모델 호출 0)

## 6. 선택적 재확인: B3 대 B4

- 거래당 조합 평가 수 중앙값 1, 최대 8; 근사 탐색(조합 64 초과) 0건.
- 미확정 항목 종류(거래 합): SELECTION_UNRESOLVED 338, M1G_AMBIGUOUS 332, OMISSION 86
- B3 CLARIFY 사유: 게이트 확인(SELECTED_MISSING,SELECTION_MISMATCH) 80, M1 확인(판정을 바꾸는 미확정 항목) 64, 게이트 확인(E2_STOCK_CLAIM_BY_CHOSEN) 60, 게이트 확인(UNKNOWN_ATTR) 30, 게이트 확인(ITEM,SELECTION_MISMATCH) 2
- 미검증 조건 정책으로 판정이 달라진 거래: 없음

| 유형 | 미확정 수 | n | (B3 판정 / B4 판정): 건수 |
|---|---|---:|---|
| authority_only | 0 | 500 | ALLOW/ALLOW: 425, CLARIFY/CLARIFY: 60, DENY/DENY: 15 |
| authority_only | 1 | 122 | ALLOW/CLARIFY: 87, CLARIFY/CLARIFY: 32, DENY/CLARIFY: 3 |
| authority_only | 2 | 16 | CLARIFY/CLARIFY: 7, ALLOW/CLARIFY: 7, DENY/CLARIFY: 2 |
| authority_only | 3+ | 1 | CLARIFY/CLARIFY: 1 |
| both | 0 | 661 | DENY/DENY: 548, ALLOW/ALLOW: 103, CLARIFY/CLARIFY: 10 |
| both | 1 | 166 | DENY/CLARIFY: 145, ALLOW/CLARIFY: 16, CLARIFY/CLARIFY: 5 |
| both | 2 | 22 | DENY/CLARIFY: 19, CLARIFY/CLARIFY: 2, ALLOW/CLARIFY: 1 |
| both | 3+ | 3 | DENY/CLARIFY: 1, ALLOW/CLARIFY: 1, CLARIFY/CLARIFY: 1 |
| context_only | 0 | 661 | DENY/DENY: 548, ALLOW/ALLOW: 103, CLARIFY/CLARIFY: 10 |
| context_only | 1 | 166 | DENY/CLARIFY: 145, ALLOW/CLARIFY: 16, CLARIFY/CLARIFY: 5 |
| context_only | 2 | 22 | DENY/CLARIFY: 19, CLARIFY/CLARIFY: 2, ALLOW/CLARIFY: 1 |
| context_only | 3+ | 3 | CLARIFY/CLARIFY: 1, DENY/CLARIFY: 1, ALLOW/CLARIFY: 1 |
| normal | 0 | 500 | ALLOW/ALLOW: 425, CLARIFY/CLARIFY: 60, DENY/DENY: 15 |
| normal | 1 | 122 | ALLOW/CLARIFY: 87, CLARIFY/CLARIFY: 32, DENY/CLARIFY: 3 |
| normal | 2 | 16 | CLARIFY/CLARIFY: 7, ALLOW/CLARIFY: 7, DENY/CLARIFY: 2 |
| normal | 3+ | 1 | CLARIFY/CLARIFY: 1 |

## 5. 조건부 조항 (AV0–AV2·AV2+·PRECHECK는 구조상 조항이 없다)

- B3 mandate 재구성: M1-G 원장 재생 적중 19100, 원장에 없는 요청 0(보내지 않음), 재구성 실패 거래 0.
- B2는 선택 상태 S를 만들지 않는다(`raw_ctx`의 selection = None). 그래서 선택에 묶인 조항·범위 검사는 B2에서 생기지 않는다.

| 대상 | 비교군 | 항목 | 건수 |
|---|---|---|---:|
| matched | B2 | 거래 | 198 |
| matched | B2 | 발동(CLAUSE_ACTIVE) | 0 |
| matched | B2 | 선택 S 있음 | 0 |
| matched | B2 | 조항 생성(1개 이상) | 0 |
| matched | B2 | 조항 합계 | 0 |
| matched | B2 | 증거·조항 실패: E2_STOCK_CLAIM_BY_CHOSEN | 61 |
| matched | B3 | 거래 | 198 |
| matched | B3 | 발동(CLAUSE_ACTIVE) | 0 |
| matched | B3 | 선택 S 있음 | 0 |
| matched | B3 | 조항 생성(1개 이상) | 0 |
| matched | B3 | 조항 합계 | 0 |
| matched | B3 | 증거·조항 실패: E2_STOCK_CLAIM_BY_CHOSEN | 65 |
| matched | B4 | 거래 | 198 |
| matched | B4 | 발동(CLAUSE_ACTIVE) | 0 |
| matched | B4 | 조항 생성(1개 이상) | 0 |
| matched | B4 | 조항 합계 | 0 |
| matched | B4 | 증거·조항 실패: E2_STOCK_CLAIM_BY_CHOSEN | 65 |
| tx | B2 | 거래 | 2982 |
| tx | B2 | 발동(CLAUSE_ACTIVE) | 0 |
| tx | B2 | 선택 S 있음 | 0 |
| tx | B2 | 조항 생성(1개 이상) | 0 |
| tx | B2 | 조항 합계 | 0 |
| tx | B2 | 증거·조항 실패: E2_STOCK_CLAIM_BY_CHOSEN | 46 |
| tx | B2 | 증거·조항 실패: UNKNOWN_ATTR | 2 |
| tx | B3 | 거래 | 2982 |
| tx | B3 | 발동(CLAUSE_ACTIVE) | 0 |
| tx | B3 | 선택 S 있음 | 2206 |
| tx | B3 | 조항 생성(1개 이상) | 76 |
| tx | B3 | 조항 합계 | 148 |
| tx | B3 | 증거·조항 실패: E2_STOCK_CLAIM_BY_CHOSEN | 62 |
| tx | B3 | 증거·조항 실패: UNKNOWN_ATTR | 42 |
| tx | B4 | 거래 | 2982 |
| tx | B4 | 발동(CLAUSE_ACTIVE) | 0 |
| tx | B4 | 조항 생성(1개 이상) | 76 |
| tx | B4 | 조항 합계 | 148 |
| tx | B4 | 증거·조항 실패: E2_STOCK_CLAIM_BY_CHOSEN | 62 |
| tx | B4 | 증거·조항 실패: UNKNOWN_ATTR | 42 |

## 4. 반복 일관성 (단위: 같은 거래의 최종 결제 판정)

- PRECHECK: 독립 반복(별도 원장, 재사용 없음) 1회차 → 2회차 전이:

| 유형 | n | 일치 | 전이(1회차→2회차) |
|---|---:|---:|---|

- B2·B3: v4 dev에서는 **독립 반복이 없다**. R-v4g의 추출은 P4 추출을 원장에서 재사용한 캐시 재현이다.
  - 고정 전 P4 행 대 R-v4g 행의 B2 판정: . 차이가 있으면 그 사이의 정책 변경(동의 시점 미검증 → CLARIFY) 때문이고, 모델 변동이 아니다.
  - B2·B3의 독립 반복은 봉인 표본 2회 실행(계획 A)에서 잰다. v4 dev에서 따로 재려면 추출과 M1-G를 새 원장으로 다시 불러야 한다(약 $0.41, 승인 필요).

