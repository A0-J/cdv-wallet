# v3 변경 후보 개입 경로 (dev): M1 v1 대 v2 혼동 행렬

- 이 경로의 통과율은 추출기 오류율이 아니다(v3 README). 이전 장부는 v3 정답 initial_state(오라클). 표지는 accepted_changes = 수용, proposed_invalid_operations = 거부.
- 생성 데이터(v3: CartTrace 카탈로그 + 합성 대화). 주 결과와 분리해 보고한다.

| 유형 | 정답 | n | v1 수용/거부/확인/미지원 | v2 수용/거부/확인/미지원 |
|---|---|---:|---|---|
| T0/omitted_condition | REJECT | 17 | 2 / 4 / 10 / 1 | 2 / 9 / 5 / 1 |
| T0/unchanged | CLARIFY | 4 | 1 / 0 / 3 / 0 | 1 / 1 / 2 / 0 |
| T0/unchanged | REJECT | 6 | 3 / 0 / 3 / 0 | 3 / 1 / 2 / 0 |
| T0/unsupported_condition | REJECT | 16 | 1 / 4 / 9 / 2 | 1 / 10 / 3 / 2 |
| T1/ADD | ACCEPT | 37 | 24 / 0 / 11 / 2 | 23 / 7 / 5 / 2 |
| T1/ADD | CLARIFY | 7 | 1 / 0 / 4 / 2 | 1 / 3 / 1 / 2 |
| T1/ADD | REJECT | 3 | 1 / 0 / 2 / 0 | 1 / 1 / 1 / 0 |
| T1/OVERRIDE | ACCEPT | 30 | 16 / 0 / 12 / 2 | 16 / 6 / 6 / 2 |
| T1/OVERRIDE | CLARIFY | 9 | 0 / 0 / 9 / 0 | 0 / 8 / 1 / 0 |
| T1/OVERRIDE | REJECT | 4 | 1 / 0 / 2 / 1 | 1 / 2 / 0 / 1 |
| T1/RELAX | ACCEPT | 27 | 15 / 0 / 9 / 3 | 13 / 3 / 8 / 3 |
| T1/RELAX | CLARIFY | 8 | 0 / 0 / 7 / 1 | 0 / 7 / 0 / 1 |
| T1/RELAX | REJECT | 2 | 1 / 0 / 1 / 0 | 1 / 0 / 1 / 0 |
| T1/REVOKE | ACCEPT | 32 | 16 / 0 / 11 / 5 | 14 / 5 / 8 / 5 |
| T1/REVOKE | CLARIFY | 8 | 1 / 0 / 4 / 3 | 1 / 2 / 2 / 3 |
| T1/REVOKE | REJECT | 3 | 0 / 0 / 3 / 0 | 0 / 1 / 2 / 0 |
| T1/SUBSTITUTE | ACCEPT | 29 | 17 / 0 / 11 / 1 | 15 / 6 / 7 / 1 |
| T1/SUBSTITUTE | CLARIFY | 7 | 1 / 0 / 5 / 1 | 1 / 3 / 2 / 1 |
| T1/SUBSTITUTE | REJECT | 4 | 0 / 1 / 3 / 0 | 0 / 3 / 1 / 0 |
| T1/TIGHTEN | ACCEPT | 33 | 19 / 0 / 11 / 3 | 18 / 7 / 5 / 3 |
| T1/TIGHTEN | CLARIFY | 5 | 1 / 0 / 4 / 0 | 1 / 3 / 1 / 0 |
| T1/TIGHTEN | REJECT | 3 | 1 / 0 / 2 / 0 | 1 / 0 / 2 / 0 |
| T2/brand | ACCEPT | 2 | 2 / 0 / 0 / 0 | 2 / 0 / 0 / 0 |
| T2/brand | CLARIFY | 5 | 0 / 0 / 5 / 0 | 0 / 1 / 4 / 0 |
| T2/brand | REJECT | 17 | 0 / 5 / 12 / 0 | 0 / 7 / 10 / 0 |
| T2/budget | ACCEPT | 1 | 1 / 0 / 0 / 0 | 1 / 0 / 0 / 0 |
| T2/budget | CLARIFY | 4 | 0 / 0 / 2 / 2 | 0 / 2 / 0 / 2 |
| T2/budget | REJECT | 17 | 2 / 2 / 11 / 2 | 2 / 11 / 2 / 2 |
| T2/false_stock | REJECT | 16 | 0 / 16 / 0 / 0 | 0 / 16 / 0 / 0 |
| T2/fulfillment_restriction | ACCEPT | 4 | 3 / 0 / 1 / 0 | 3 / 1 / 0 / 0 |
| T2/fulfillment_restriction | CLARIFY | 1 | 0 / 0 / 1 / 0 | 0 / 1 / 0 / 0 |
| T2/fulfillment_restriction | REJECT | 16 | 1 / 3 / 12 / 0 | 1 / 12 / 3 / 0 |
| T2/product_attribute | ACCEPT | 4 | 3 / 0 / 1 / 0 | 3 / 1 / 0 / 0 |
| T2/product_attribute | CLARIFY | 1 | 0 / 0 / 1 / 0 | 0 / 1 / 0 / 0 |
| T2/product_attribute | REJECT | 17 | 1 / 3 / 13 / 0 | 1 / 12 / 4 / 0 |
| T2/quantity_bundle | ACCEPT | 4 | 2 / 0 / 2 / 0 | 2 / 0 / 2 / 0 |
| T2/quantity_bundle | CLARIFY | 2 | 0 / 0 / 2 / 0 | 0 / 2 / 0 / 0 |
| T2/quantity_bundle | REJECT | 17 | 0 / 6 / 10 / 1 | 0 / 11 / 5 / 1 |
| T3/budget | ACCEPT | 1 | 0 / 0 / 1 / 0 | 0 / 1 / 0 / 0 |
| T3/budget | CLARIFY | 11 | 2 / 0 / 8 / 1 | 2 / 3 / 5 / 1 |
| T3/budget | REJECT | 6 | 3 / 0 / 2 / 1 | 2 / 1 / 2 / 1 |
| T3/induced_consent | CLARIFY | 16 | 0 / 0 / 16 / 0 | 0 / 0 / 16 / 0 |
| T3/reference | ACCEPT | 4 | 2 / 0 / 2 / 0 | 2 / 0 / 2 / 0 |
| T3/reference | CLARIFY | 13 | 2 / 0 / 8 / 3 | 2 / 4 / 4 / 3 |
| T3/reference | REJECT | 4 | 1 / 0 / 3 / 0 | 1 / 3 / 0 / 0 |
| T3/revocation | ACCEPT | 3 | 1 / 0 / 2 / 0 | 1 / 1 / 1 / 0 |
| T3/revocation | CLARIFY | 14 | 1 / 0 / 11 / 2 | 1 / 3 / 8 / 2 |
| T3/revocation | REJECT | 4 | 3 / 0 / 1 / 0 | 3 / 1 / 0 / 0 |
| ALL | ACCEPT | 211 | 121 / 0 / 74 / 16 | 113 / 38 / 44 / 16 |
| ALL | CLARIFY | 115 | 10 / 0 / 90 / 15 | 10 / 44 / 46 / 15 |
| ALL | REJECT | 172 | 21 / 44 / 99 / 8 | 20 / 101 / 43 / 8 |
