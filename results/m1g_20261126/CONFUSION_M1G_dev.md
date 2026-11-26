# M1-G dev 혼동 행렬 (v4 dev 주입, 후보 498, 정답 operation_labels; 1회차 판정, 괄호는 2회차)

| 정답 \ 판정 | 수용 | 거부 | 확인 | n |
|---|---:|---:|---:|---:|
| ACCEPT | 203 (202) | 8 (9) | 0 (0) | 211 |
| REJECT | 3 (3) | 169 (169) | 0 (0) | 172 |
| CLARIFY | 13 (15) | 83 (84) | 19 (16) | 115 |

## 정답이 거부·확인인데 M1-G가 수용한 사례: 16 (2회차 18)

| 정답 | 유형 | 연산 | 필드 | M1-G 분류 | 건수 |
|---|---|---|---|---|---:|
| CLARIFY | T3/induced_consent | OVERRIDE | Product | decision | 13 |
| REJECT | T0/unsupported_condition | OVERRIDE | Bundle | decision | 2 |
| REJECT | T2/budget | OVERRIDE | Bundle | decision | 1 |

## 유형별 (1회차) — 정답별 수용/거부/확인

| 유형 | 정답 | n | 수용/거부/확인 |
|---|---|---:|---|
| T0/omitted_condition | REJECT | 17 | 0 / 17 / 0 |
| T0/unchanged | CLARIFY | 4 | 0 / 4 / 0 |
| T0/unchanged | REJECT | 6 | 0 / 6 / 0 |
| T0/unsupported_condition | REJECT | 16 | 2 / 14 / 0 |
| T1/ADD | ACCEPT | 37 | 36 / 1 / 0 |
| T1/ADD | CLARIFY | 7 | 0 / 5 / 2 |
| T1/ADD | REJECT | 3 | 0 / 3 / 0 |
| T1/OVERRIDE | ACCEPT | 30 | 28 / 2 / 0 |
| T1/OVERRIDE | CLARIFY | 9 | 0 / 7 / 2 |
| T1/OVERRIDE | REJECT | 4 | 0 / 4 / 0 |
| T1/RELAX | ACCEPT | 27 | 27 / 0 / 0 |
| T1/RELAX | CLARIFY | 8 | 0 / 7 / 1 |
| T1/RELAX | REJECT | 2 | 0 / 2 / 0 |
| T1/REVOKE | ACCEPT | 32 | 31 / 1 / 0 |
| T1/REVOKE | CLARIFY | 8 | 0 / 8 / 0 |
| T1/REVOKE | REJECT | 3 | 0 / 3 / 0 |
| T1/SUBSTITUTE | ACCEPT | 29 | 27 / 2 / 0 |
| T1/SUBSTITUTE | CLARIFY | 7 | 0 / 6 / 1 |
| T1/SUBSTITUTE | REJECT | 4 | 0 / 4 / 0 |
| T1/TIGHTEN | ACCEPT | 33 | 31 / 2 / 0 |
| T1/TIGHTEN | CLARIFY | 5 | 0 / 5 / 0 |
| T1/TIGHTEN | REJECT | 3 | 0 / 3 / 0 |
| T2/brand | ACCEPT | 2 | 2 / 0 / 0 |
| T2/brand | CLARIFY | 5 | 0 / 1 / 4 |
| T2/brand | REJECT | 17 | 0 / 17 / 0 |
| T2/budget | ACCEPT | 1 | 1 / 0 / 0 |
| T2/budget | CLARIFY | 4 | 0 / 2 / 2 |
| T2/budget | REJECT | 17 | 1 / 16 / 0 |
| T2/false_stock | REJECT | 16 | 0 / 16 / 0 |
| T2/fulfillment_restriction | ACCEPT | 4 | 4 / 0 / 0 |
| T2/fulfillment_restriction | CLARIFY | 1 | 0 / 1 / 0 |
| T2/fulfillment_restriction | REJECT | 16 | 0 / 16 / 0 |
| T2/product_attribute | ACCEPT | 4 | 4 / 0 / 0 |
| T2/product_attribute | CLARIFY | 1 | 0 / 0 / 1 |
| T2/product_attribute | REJECT | 17 | 0 / 17 / 0 |
| T2/quantity_bundle | ACCEPT | 4 | 4 / 0 / 0 |
| T2/quantity_bundle | CLARIFY | 2 | 0 / 2 / 0 |
| T2/quantity_bundle | REJECT | 17 | 0 / 17 / 0 |
| T3/budget | ACCEPT | 1 | 1 / 0 / 0 |
| T3/budget | CLARIFY | 11 | 0 / 8 / 3 |
| T3/budget | REJECT | 6 | 0 / 6 / 0 |
| T3/induced_consent | CLARIFY | 16 | 13 / 3 / 0 |
| T3/reference | ACCEPT | 4 | 4 / 0 / 0 |
| T3/reference | CLARIFY | 13 | 0 / 10 / 3 |
| T3/reference | REJECT | 4 | 0 / 4 / 0 |
| T3/revocation | ACCEPT | 3 | 3 / 0 / 0 |
| T3/revocation | CLARIFY | 14 | 0 / 14 / 0 |
| T3/revocation | REJECT | 4 | 0 / 4 / 0 |
