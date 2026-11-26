# 개발 평가 보고 (validation, m2fix_brand; 개발 단계 결과)

모든 표: [개발 분할(validation), 정책 두 가지 조정 후] — 브랜드 판정(상품명 일치), 선택 불일치만 있으면 CLARIFY. 최종 결과가 아니다.

[개발 분할(validation), 정책 두 가지 조정 후] 정상(RIGHT/RIGHT_BY_LUCK) 235여정, 비교군별 판정. 'ALLOW(미검증 조건 있음)' = 서명된 Mandate에 수령 방식·기한이 있으나 장바구니 단계 결제 요청에 그 정보가 없어 검사하지 못하고 통과한 경우(충족으로 세지 않음).

| 비교군 | ALLOW | ALLOW(unverified condition) | CLARIFY:M1 | CLARIFY:selection | CLARIFY:unknown_attr | CLARIFY:E2 | CLARIFY:other_gate | DENY |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B0 | 235 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| B1 | 89 | 0 | 146 | 0 | 0 | 0 | 0 | 0 |
| B2 | 137 | 70 | 0 | 0 | 13 | 0 | 0 | 15 |
| B3 | 128 | 65 | 7 | 7 | 17 | 0 | 1 | 10 |
| B4 | 46 | 34 | 146 | 5 | 1 | 0 | 0 | 3 |
| v1 | 114 | 0 | 117 | 0 | 0 | 0 | 0 | 4 |

- 주석: **B1(M1 Only)은 결제 시점 강제가 없어 DENY를 낼 수 없다**(구조상 0). B0은 공통 결제 보안만 있는 바닥값이다. v1은 PLAN_v3 규칙 + M2a 연결 행이다.
- 수령 방식·기한 조건이 Mandate에 있는 여정 비율(전체 306): B2 34.6%, B3 33.0%, B4 33.0% (B0·B1은 Mandate가 장바구니 서명뿐이라 해당 없음).

## 여정 단위 McNemar (정상 여정, 차단 = CLARIFY 또는 DENY) [개발 분할(validation), 정책 두 가지 조정 후]

| 비교 | 앞쪽만 차단 | 뒤쪽만 차단 | p(정확) |
|---|---:|---:|---:|
| B3 vs B4 | 0 | 113 | 0.0 |
| B3 vs B1 | 9 | 113 | 0.0 |
| B3 vs B2 | 17 | 3 | 0.0026 |

## WRONG/WRONG_HIDDEN 여정 (탐지율로 해석하지 않음) [개발 분할(validation), 정책 두 가지 조정 후]

| 부분집합 | n | B0 | B1 | B2 | B3 | B4 | v1 |
|---|---:|---|---|---|---|---|---|
| U 참고값이 막음 | 29 | A29 / C0 / D0 | A7 / C22 / D0 | A13 / C2 / D14 | A12 / C4 / D13 | A5 / C20 / D4 | A11 / C15 / D3 |
| U 참고값도 통과 | 42 | A42 / C0 / D0 | A13 / C29 / D0 | A40 / C1 / D1 | A39 / C3 / D0 | A11 / C31 / D0 | A19 / C23 / D0 |

- 'U 참고값도 통과' 여정은 결제 시점에 검사할 수 있는 진술 조건(예산·수량·브랜드·묶음 수)을 어기지 않았다. 이 여정의 CLARIFY/DENY는 위반 탐지가 아니다.

## B2(M2 Only)와 B3(M1+M2)의 판정이 다른 여정: 36 [개발 분할(validation), 정책 두 가지 조정 후]

| 집단 | 판정 변화 | 원인 | 여정 |
|---|---|---|---:|
| legit | B2 ALLOW -> B3 CLARIFY | selection S | 7 |
| legit | B2 DENY -> B3 CLARIFY | verification: unresolved M1 item changes the decision | 5 |
| wrong | B2 ALLOW -> B3 CLARIFY | verification: unresolved M1 item changes the decision | 3 |
| legit | B2 DENY -> B3 ALLOW | verification: B2 used an unverified extractor value (MAX_TOTAL_WITH_FEES) | 2 |
| legit | B2 ALLOW -> B3 CLARIFY | verification: verified ledger differs (UNKNOWN_ATTR) | 2 |
| legit | B2 ALLOW -> B3 CLARIFY | product kind | 2 |
| wrong | B2 DENY -> B3 ALLOW | verification: B2 used an unverified extractor value (MAX_TOTAL_WITH_FEES) | 2 |
| legit | B2 ALLOW -> B3 CLARIFY | verification: unresolved M1 item changes the decision | 2 |
| wrong | B2 DENY -> B3 CLARIFY | verification: unresolved M1 item changes the decision | 1 |
| wrong | B2 ALLOW -> B3 DENY | verification: verified ledger differs (MAX_TOTAL_WITH_FEES) | 1 |
| legit | B2 CLARIFY -> B3 ALLOW | verification: B2 used an unverified extractor value (UNKNOWN_ATTR) | 1 |
| wrong | B2 CLARIFY -> B3 DENY | selection S | 1 |
| wrong | B2 DENY -> B3 ALLOW | verification: B2 used an unverified extractor value (QUANTITY) | 1 |
| legit | B2 ALLOW -> B3 DENY | verification: verified ledger differs (BRAND,BUNDLE_MEMBER_MISSING) | 1 |
| legit | B2 ALLOW -> B3 CLARIFY | verification: verified ledger differs (EVIDENCE_MISSING) | 1 |
| legit | B2 DENY -> B3 CLARIFY | verification: verified ledger differs (UNKNOWN_ATTR) | 1 |
| legit | B2 ALLOW -> B3 DENY | verification: verified ledger differs (BUNDLE_MEMBER_MISSING) | 1 |
| wrong | B2 ALLOW -> B3 CLARIFY | verification: verified ledger differs (EVIDENCE_MISSING) | 1 |
| legit | B2 ALLOW -> B3 DENY | verification: verified ledger differs (BRAND) | 1 |
