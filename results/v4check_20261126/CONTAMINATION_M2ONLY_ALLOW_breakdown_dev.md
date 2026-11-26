# 결함 주입: M2 Only가 맥락 위반 거래를 부당 허용한 사례의 분포 (v4 dev)

- 맥락 위반 거래(context_only) 430건 중 M2 Only ALLOW 61건. 같은 여정의 비수용 후보 연산 기준.

## 여정 유형

- T2/product_attribute: 11
- T0/omitted_condition: 8
- T2/fulfillment_restriction: 8
- T2/quantity_bundle: 7
- T0/unsupported_condition: 7
- T3/budget: 4
- T0/unchanged: 3
- T2/brand: 3
- T3/reference: 2
- T2/budget: 2
- T3/revocation: 2
- T1/REVOKE: 1
- T1/SUBSTITUTE: 1
- T1/TIGHTEN: 1
- T1/ADD: 1

## 원인(gold cause)

- none: 61

## 비수용 후보 연산(연산, 필드, 정답)

| 연산 | 필드 | 정답 | 건수 |
|---|---|---|---:|
| REVOKE | Deadline | reject | 17 |
| OVERRIDE | Quantity | reject | 11 |
| REVOKE | Fulfillment | reject | 10 |
| OVERRIDE | Fulfillment | reject | 8 |
| RELAX | Price | reject | 8 |
| REVOKE | Price | reject | 7 |
| REVOKE | Deadline | clarify | 2 |
