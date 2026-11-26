# validation 진단 (arms2 행, 무과금) [개발 분할(validation), 정책 조정 후]

## B3 정상 여정 DENY의 원인 코드

- {('BUNDLE_MEMBER_MISSING',): 3, ('BUNDLE_MEMBER_MISSING', 'QUANTITY'): 1, ('BRAND',): 4, ('BRAND', 'BUNDLE_MEMBER_MISSING'): 1, ('QUANTITY',): 1}

## 미확정 항목 수 k 분포(여정, B3의 M1 v2)

- k: {0: 109, 1: 150, 2: 34, 3: 12, 4: 1} (9는 9 이상). 조합 검사 수: {1: 116, 2: 152, 4: 35, 8: 3}. 64조합 초과로 근사한 여정: 0

## 미검증 필수 조건 두 정책

- record(현행): 장바구니·결제 동의 모두 'ALLOW(미검증)'으로 기록.
- consent: 결제 동의 시점에 미검증 조건이 남으면 CLARIFY, 장바구니 전달 단계는 'PROCEED(미검증)'(최종 지불 허용 아님).

| 비교군 | 정책 | 정상 235 | 결제 시점 위반 부분집합 |
|---|---|---|---|
| B2 | record | {'CLARIFY': 13, 'ALLOW': 137, 'ALLOW(미검증)': 70, 'DENY': 15} | {'ALLOW': 11, 'DENY': 14, 'ALLOW(미검증)': 2, 'CLARIFY': 2} |
| B2 | consent | {'CLARIFY': 13, 'ALLOW': 137, 'PROCEED(장바구니 단계, 미검증)': 54, 'CLARIFY(결제 동의 시점 미검증)': 16, 'DENY': 15} | {'ALLOW': 11, 'DENY': 14, 'PROCEED(장바구니 단계, 미검증)': 2, 'CLARIFY': 2} |
| B3 | record | {'CLARIFY': 32, 'ALLOW': 128, 'ALLOW(미검증)': 65, 'DENY': 10} | {'ALLOW': 10, 'DENY': 13, 'CLARIFY': 4, 'ALLOW(미검증)': 2} |
| B3 | consent | {'CLARIFY': 32, 'ALLOW': 128, 'PROCEED(장바구니 단계, 미검증)': 53, 'CLARIFY(결제 동의 시점 미검증)': 12, 'DENY': 10} | {'ALLOW': 10, 'DENY': 13, 'CLARIFY': 4, 'PROCEED(장바구니 단계, 미검증)': 2} |
| B4 | record | {'CLARIFY': 152, 'ALLOW': 46, 'ALLOW(미검증)': 34, 'DENY': 3} | {'CLARIFY': 20, 'DENY': 4, 'ALLOW': 4, 'ALLOW(미검증)': 1} |
| B4 | consent | {'CLARIFY': 152, 'ALLOW': 46, 'PROCEED(장바구니 단계, 미검증)': 28, 'CLARIFY(결제 동의 시점 미검증)': 6, 'DENY': 3} | {'CLARIFY': 20, 'DENY': 4, 'ALLOW': 4, 'PROCEED(장바구니 단계, 미검증)': 1} |
