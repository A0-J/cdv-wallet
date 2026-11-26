# v4 dev: 참조 cart_reasons() 대 우리 M2 범위 검사 (둘 다 정답 effective_state 기준, 모델 호출 0)

- 거래 1482건. 우리 게이트 판정 분포: {'DENY': 650, 'ALLOW': 692, 'CLARIFY': 140}. '참조 위반 있음' 대 '우리 판정이 ALLOW 아님' 일치: 1204/1482. 필드별 표는 DENY 사유만 센다.

| 필드 | 둘 다 위반 | 참조만 위반 | 우리만 위반 |
|---|---:|---:|---:|
| Brand | 72 | 0 | 0 |
| Deadline | 240 | 0 | 0 |
| Fulfillment | 260 | 2 | 0 |
| Price | 4 | 214 | 0 |
| Quantity | 146 | 2 | 4 |
