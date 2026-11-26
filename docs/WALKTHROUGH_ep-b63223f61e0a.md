# 전체 동작 예시: ep-b63223f61e0a (CartTrace validation, 결과 WRONG)

> **주의:** 2단계의 FnCTOD 출력은 설명용으로 사람이 쓴 값이다(모델 출력 아님). 유료 실행 승인 뒤 실제 출력으로 바꾼다.
> CartTrace 발화는 CC BY 4.0(generalmachines/CartTrace-100k)이며 짧게 발췌했다.

## 1. 원본 (사용자 발화만, 순서대로)
- `s2` I'd like the Tire Pressure Sensor and the RXR FULL FACE HELMET together in one order, one of each. I'd rather collect it in store.
- `s13` I'll go with Tire Pressure Sensor.
- `s17` I'll go with muted black.
- `s31` Yes, place the order for $112.30.
- `s55` No preference on the color. If it is out of stock, just tell me.
- `s63` I'll go with Helmet.
- `s78` That isn't what I asked for. Don't place the order.

- 숨은 사양(채점에만 씀): I want the Tire Pressure Sensor and the RXR FULL FACE HELMET together, one of each; 2 different items; one of each, 2 in all
- 기록된 최종 장바구니: [('RXR Motorcycle DUAL VISOR FULL FACE HELMET WI', 89.99, 1)]

## 2. FnCTOD 추출 (사용자 턴마다 2단계: 함수 선택 → 인자 생성)
- `s2` 선택 ['set_purchase_conditions'] → 상태 {"required_items": ["Tire Pressure Sensor", "RXR FULL FACE HELMET"], "quantity": 2, "fulfillment": "pickup"}
- `s13` 선택 ['none'] → 상태 {"required_items": ["Tire Pressure Sensor", "RXR FULL FACE HELMET"], "quantity": 2, "fulfillment": "pickup"}
- `s17` 선택 ['none'] → 상태 {"required_items": ["Tire Pressure Sensor", "RXR FULL FACE HELMET"], "quantity": 2, "fulfillment": "pickup"}
- `s31` 선택 ['none'] → 상태 {"required_items": ["Tire Pressure Sensor", "RXR FULL FACE HELMET"], "quantity": 2, "fulfillment": "pickup"}
- `s55` 선택 ['none'] → 상태 {"required_items": ["Tire Pressure Sensor", "RXR FULL FACE HELMET"], "quantity": 2, "fulfillment": "pickup"}
- `s63` 선택 ['set_purchase_conditions'] → 상태 {"required_items": ["RXR FULL FACE HELMET"], "quantity": 1, "fulfillment": "pickup"}
- `s78` 선택 ['none'] → 상태 {"required_items": ["RXR FULL FACE HELMET"], "quantity": 1, "fulfillment": "pickup"}

## 3. M1 검증 (fnctod_r: 규칙. FnCTOD는 인용을 내지 않으므로 M1이 사용자 발화 전체에서 근거를 찾는다)
- `s2` 연산 add `bundle` · 근거 찾기 rule · 판정 **ACCEPT** ['NARROW']
- `s2` 연산 add `ful` · 근거 찾기 rule · 판정 **ACCEPT** ['NARROW']
- `s2` 연산 add `qty` · 근거 찾기 none · 판정 **REJECT** ['NON_USER_SOURCE']
- `s63` 연산 revoke `bundle` · 근거 찾기 none · 판정 **REJECT** ['NON_USER_SOURCE']
- (상태가 그대로라 같은 연산이 다음 턴에 다시 제안된 경우는 한 번만 적었다.)
- 결제 전 판정 힌트: **OK**, 대기 [], 경보 []

## 4. Mandate 생성과 서명 (검증된 장부만 서명, ECDSA P-256)
- mandate 본문: `{"ledger": {"bundle": ["Tire Pressure Sensor", "RXR FULL FACE HELMET"], "ful": "pickup"}, "pending": [], "episode": "ep-b63223f61e0a"}`
- 본문 sha256: `85ed517e7203c59d…`, 서명 `es256:3044022031c7f7dc84…`, 공개키 검증 True
- 대기 항목이 있으면 사용자 확인 전에는 결제 권한을 발급하지 않는다(CLARIFY).

## 5. M2 거래 검증 (기록된 장바구니 vs 장부)과 비교군
- fnctod_rn(규칙 + NLI) 근거 찾기: `s2` add `qty` nli → PENDING
| 비교군 | 서명되는 장부 | M1 힌트 | M2 장바구니 검사 | 최종 |
|---|---|---|---|---|
| fnctod (검증 없음) | {"quantity": 1, "fulfillment": "pickup"} | OK | ALLOW [] | **ALLOW** |
| fnctod_r (FnCTOD + M1 규칙) | {"bundle_all": ["Tire Pressure Sensor", "RXR FULL FACE HELMET"], "fulfillment": "pickup"} | OK | DENY ['BUNDLE_MEMBER_MISSING'] | **DENY** |
| fnctod_rn (+ NLI) | {"bundle_all": ["Tire Pressure Sensor", "RXR FULL FACE HELMET"], "fulfillment": "pickup"} | CLARIFY | DENY ['BUNDLE_MEMBER_MISSING'] | **DENY** |

- 실제 쇼핑객은 이 장바구니를 결제 단계에서 거절했다(`s78`). 정답 동작은 ALLOW가 아니다.
- fnctod는 모호한 고르기를 묶음 철회로 받아들여 헬멧만 담은 장바구니를 ALLOW한다.
- fnctod_r: `s63`의 "I'll go with Helmet."은 고르기일 뿐 철회 단서(WIDEN_CUES)가 없다. 그래서 묶음 철회를 받아들이지 않고, 묶음이 남은 장부로 장바구니를 검사해 빠진 품목(BUNDLE_MEMBER_MISSING)으로 막는다.
- fnctod_r 장부에 수량이 빠진 것은 규칙 근거 찾기가 실패했기 때문이다(아래 6절).

## 6. 이 사례에서 드러난 한계 (그대로 적음)
- 수량: FnCTOD가 낸 값 2(총 개수)를 사용자 표현 "one of each"에서 규칙으로 찾지 못해 장부에서 빠졌다. NLI 팔 결과는 5절 표에 있다(이 한 사례만 보고, 일반화하지 않는다).
- 2026-11-26 이 사례를 돌리다 규칙 두 개를 고쳤다(validation 사례, 시험 분할 아님): "collect it in store"를 매장 수령으로 인식, "If it is out of stock, just tell me"를 조건부 대체 허용으로 읽지 않음. 누락 검사 재실행 결과: `results/omission_realtext_20261126/summary_*_v3_rulefix.json`.
