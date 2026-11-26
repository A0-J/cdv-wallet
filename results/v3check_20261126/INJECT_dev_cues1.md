# v3 변경 후보 개입 경로 (dev): M1 v1 대 v2 혼동 행렬

- 이 경로의 통과율은 추출기 오류율이 아니다(v3 README). 이전 장부는 v3 정답 initial_state(오라클). 표지는 accepted_changes = 수용, proposed_invalid_operations = 거부.
- 생성 데이터(v3: CartTrace 카탈로그 + 합성 대화). 주 결과와 분리해 보고한다.

| 유형 | 정답 | n | v1 수용/거부/확인/미지원 | v2 수용/거부/확인/미지원 |
|---|---|---:|---|---|
| T0/omitted_condition | REJECT | 17 | 0 / 0 / 17 / 0 | 0 / 17 / 0 / 0 |
| T0/unsupported_condition | REJECT | 16 | 0 / 0 / 0 / 16 | 0 / 0 / 0 / 16 |
| T1/ADD | ACCEPT | 35 | 22 / 0 / 13 / 0 | 22 / 5 / 8 / 0 |
| T1/OVERRIDE | ACCEPT | 28 | 19 / 0 / 9 / 0 | 19 / 2 / 7 / 0 |
| T1/RELAX | ACCEPT | 23 | 6 / 0 / 17 / 0 | 6 / 0 / 17 / 0 |
| T1/REVOKE | ACCEPT | 30 | 11 / 0 / 10 / 9 | 11 / 2 / 8 / 9 |
| T1/SUBSTITUTE | ACCEPT | 28 | 5 / 0 / 23 / 0 | 5 / 1 / 22 / 0 |
| T1/TIGHTEN | ACCEPT | 31 | 27 / 0 / 4 / 0 | 27 / 1 / 3 / 0 |
| T2/brand | REJECT | 17 | 8 / 9 / 0 / 0 | 0 / 9 / 8 / 0 |
| T2/budget | REJECT | 17 | 0 / 7 / 10 / 0 | 0 / 7 / 10 / 0 |
| T2/false_stock | REJECT | 16 | 0 / 16 / 0 / 0 | 0 / 16 / 0 / 0 |
| T2/fulfillment_restriction | REJECT | 16 | 0 / 8 / 8 / 0 | 0 / 8 / 8 / 0 |
| T2/product_attribute | REJECT | 17 | 10 / 7 / 0 / 0 | 0 / 7 / 10 / 0 |
| T2/quantity_bundle | REJECT | 17 | 2 / 14 / 1 / 0 | 2 / 15 / 0 / 0 |
| T3/induced_consent | CLARIFY | 48 | 0 / 0 / 48 / 0 | 0 / 0 / 48 / 0 |
| ALL | ACCEPT | 175 | 90 / 0 / 76 / 9 | 90 / 11 / 65 / 9 |
| ALL | CLARIFY | 48 | 0 / 0 / 48 / 0 | 0 / 0 / 48 / 0 |
| ALL | REJECT | 133 | 20 / 61 / 36 / 16 | 2 / 79 / 36 / 16 |
