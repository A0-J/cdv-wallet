# 계획: M1 누락 검사(V-B)의 CartTrace 실제 발화 평가 (계산 전에 작성)

- 작성: 2026-11-26 밤. 모델 호출: 0
- 데이터
  - CartTrace 원본(리비전 `86cab5e5`). 사용자 발화는 쇼핑객 턴 전체를 쓴다(첫 발화 포함, 순서대로).
  - 개발: validation, 평가: test_cross_store
  - test_cross_store는 이전 실험에서 이미 한 번 썼다. 이 결과는 사후 분석으로 표시한다.
- 코드
  - `eval/carttrace/omission_realtext.py`
  - 검사기: `cdv/m1.py`의 `scan_omissions`. 이 계획의 커밋 전에 패턴을 고정했다.
- 대상 여정: kind=baseline. 정답 조건이 하나 이상 있는 여정

## 정답 장부 (숨은 사양에서 만듦. 정답 mandate이므로 기능 검증·상한 성격)

- 조건 출처가 stated 또는 on_ask인 조건을 쓴다. default는 쓰지 않는다.

| 숨은 사양 | 장부 필드 |
|---|---|
| `max_price` | budget_max(센트 → 통화 단위) |
| `count` | quantity |
| `all_of` | bundle_all(상품 ID). known_items는 각 상품 제목의 앞 세 단어 |
| `brand` | brand_in |
| `excludes` | brand_out |
| `prefer` | substitute(intents.substitute) |
| buyer.fulfillment(stated/on_ask) | fulfillment(pickup / ship) |
| buyer.fulfillment.deadline_days(값이 있을 때) | deadline_days |

- known_brands: brand 조건 값과 묶음 상품 제목의 첫 단어

## 측정

1. **오경보율:** 정답 장부를 그대로 넣었을 때 `OMITTED_*`가 나온 여정의 비율(필드별)
   - 사양에 없는 조건을 사용자가 말한 경우도 여기에 잡힌다. 그래서 필드별로 표본을 읽어 "진짜 오경보"와 "사양 밖 진술"을 나눈다. AI가 1차, 연구자가 2차로 본다.
2. **탐지율:** stated 조건 하나를 장부에서 지웠을 때 그 필드의 `OMITTED_*`가 나온 비율(필드별)
   - 분모는 그 필드가 stated인 여정이다.
3. **지연:** 여정당 검사 시간(중앙값, 95백분위)

## 예상 (결과를 보기 전)

- 예산과 조건부 대체의 탐지율은 높을 것이다(첫 발화가 사양 문장에서 나옴).
- 수량, 배송, 수령은 낮을 것이다. on_ask 진술이 모델 문장으로 바뀌어 패턴 밖일 수 있다.
- 브랜드와 묶음은 known 목록에 좌우된다.
- 오경보는 수령 조건(pickup)과 배송 기한에서 생길 수 있다.

## 한계

- 정답 장부를 입력하므로 추출기 성능과 무관한 검사기 단독 측정이다.
- 패턴 규칙이라 표현 다양성에 약하다. 놓친 경우는 NLI 단계의 몫이다.

---

## 덧붙임 v2 (개발용 결과를 본 뒤, 평가용 계산 전에 작성)

- v1 개발용 결과는 `summary_validation_v1.json`에 그대로 남겼다.
- 개발용 오경보와 놓침 표본을 읽고 다음을 바꿨다. 평가용(test_cross_store)은 아직 계산하지 않았다.
  1. **known_brands:** 묶음 상품 제목의 첫 단어를 뺐다. 상품명이지 브랜드 조건이 아니다(v1 브랜드 오경보 15.9%의 원인). 브랜드 단서에서 관사(a, an, the)와 want, prefer를 뺐다.
  2. **수령 조건(배송):** "standard / regular / express delivery is fine", "send it express"를 배송 진술로 추가했다.
  3. **묶음:** 카탈로그 상품명과 사용자가 부르는 이름이 달라서 이름 일치로는 못 찾는다(예: "JML Air Stick" vs "JML Styler Hair Dryer"). 묶음 단서("one of each", "together", "in one order")만 있어도 묶음 조건이 있어야 하는 것으로 본다.
  4. **수량:** "one of each"는 묶음 품목 수를 수량으로 본다.
- "as many as my budget allows" 같은 예산 연동 수량은 다루지 않는다(한계).
