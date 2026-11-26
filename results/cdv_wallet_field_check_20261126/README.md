# CDV-Wallet 데이터 적합성 점검: CartTrace-100k (2026-11-26)

- 무과금 점검이다. 모델 호출은 0회다.
- 대상 설계: `docs/design/cdv_wallet_design_v2_20261126.md` §9(데이터)
- 데이터: `C:\ct` 로컬 사본(출처는 `C:\ct\PROVENANCE.txt`). 데이터는 저장소에 넣지 않았다.
- 스크립트: `eval/carttrace/carttrace_field_check.py`
- 결과 파일: `summary.json`. 집계 숫자만 담았고, 대화·상품·페르소나 글은 넣지 않았다.

## 질문

1. CartTrace에 사용자가 대화 중 조건을 바꾸는(완화, 덮어쓰기, 철회, 우선순위 변경) 정당 변경이 있는가?
2. 턴별 정답 조건 장부를 결정적으로 만들 수 있는가?

## 결과

**1. 숨은 사양(`hidden_spec`)에는 예정된 변경 필드가 없다.**
- 조건(predicate)의 출처는 세 가지뿐이다: `stated`(첫 발화), `on_ask`(물으면 공개), `default`.

| split | 여정 | stated | on_ask | default |
|---|---:|---:|---:|---:|
| train | 77,765 | 188,876 | 36,852 | 56,495 |
| validation | 4,199 | 10,311 | 1,929 | 3,018 |
| test_cross_store | 10,334 | 24,687 | 4,806 | 7,647 |
| test_cross_template | 9,118 | 15,139 | 4,933 | 7,882 |

**2. 첫 발화 뒤의 쇼핑객 턴에 변경 표현은 사실상 없다.**
- 변경 표현 정규식(changed my mind, scratch that, no longer, raise my budget 등)에 걸린 턴:
  - validation: 7,848턴 중 1턴
  - test_cross_store: 19,467턴 중 1턴
  - test_cross_template: 17,056턴 중 3턴

**3. 첫 발화 뒤 쇼핑객 턴의 종류** (validation, 대략적인 정규식이라 첫 일치 기준)

| 종류 | 턴 수 |
|---|---:|
| 기타(주로 질문에 대한 답, 조건 공개) | 3,939 |
| 확인(yes, go ahead 등) | 1,711 |
| 보여 준 것 중 고르기(go with X, that one 등) | 1,239 |
| 위임(go with whatever fits 등) | 554 |
| 거절(none of those 등) | 405 |

**4. 물으면 공개되는 조건(`on_ask`)의 공개 시점을 결정적으로 찾을 수 없다.**
- 첫 발화 뒤 쇼핑객 턴은 모두 모델이 바꿔 쓴 문장이다(`wording`: validation에서 model 7,512, fallback 336, 원문 그대로 0).
- 사양의 `say` 문장과 이후 쇼핑객 턴의 단어 겹침이 0.6 이상인 경우를 세었다:
  - validation: 1,929개 중 135개(7.0%)
  - test_cross_store: 4,806개 중 408개(8.5%)
  - test_cross_template: 4,933개 중 534개(10.8%)
- 앞선 PLAN_ADD3 F 점검(글자 일치 13.8%)과 같은 방향의 결과다.

**5. 진짜 품절(store fault `stockout`)과 조건부 대체가 함께 있는 여정이 있다.**
- 모두 `intents.substitute` 템플릿이다. 첫 발화가 "…, or the closest thing to it if it's out of stock" 형태다.
- 수: train 7,940 / validation 474 / test_cross_store 887 / test_cross_template 0
- validation 474건의 결과:
  - RIGHT 202
  - WRONG_REFUSAL 151
  - WRONG 85
  - WRONG_HIDDEN 14
  - CORRECT_REFUSAL 11
  - RIGHT_BY_LUCK 11

## 판단 (AI 1차, 연구자 검토 전)

- **CartTrace가 줄 수 있는 것**
  - 조건 추가(공개)
  - 보여 준 것 중 고르기(참조)
  - 위임
  - 거절
  - 신뢰 출처(상점)의 진짜 품절에서 일어나는 조건부 대체. 설계 v2의 사례 3에서 정당한 경로에 해당한다.
- **CartTrace가 줄 수 없는 것**
  - 완화, 덮어쓰기, 철회, 우선순위 변경 같은 실제 사용자 수정
  - 이것들은 템플릿으로 합성해 넣어야 한다. 정답은 구성 과정에서 알 수 있다.
- **턴별 정답 장부는 결정적으로 만들 수 없다.** 그래서 다음처럼 평가한다.
  - 기본 조건은 `stated`와 `default`, 그리고 템플릿으로 넣은 턴만 정답으로 쓴다.
  - `on_ask` 조건에 걸리는 장바구니는 평가 사례에서 뺀다.
  - 턴별 전이 정확도는 템플릿으로 넣은 턴에서만 잰다.
- 설계 v2 §9 S1의 "실제 사용자 수정 턴" 서술은 틀렸다. 설계 v2 §17에서 정정했다.

## 한계

- 턴 종류와 변경 표현은 정규식으로 센 대략값이다. 사람이 읽고 확인하지 않았다.
- 단어 겹침 기준 0.6은 이 점검에서 정한 값이다. 사전등록하지 않았다.
- 턴 수준 집계에서는 train split을 읽지 않았다.

## 덧붙임 1 (같은 날): 품절 → 다른 상품 선택 → 결제 단계에서 거절 (연구자 지적)

**연구자 지적**
- CartTrace에는 다음 흐름의 사례가 있다: 상품이 품절된다 → 쇼핑객이 다른 상품을 고른다 → 최종 결제에서 구매를 거절한다.

**확인**
- 사례가 있다.
- 위 결과 2의 "변경 표현이 사실상 없다"는 결론은 너무 강했다. 원인은 두 가지다.
  - 정규식이 "changed my mind" 같은 명시적 변경 표현만 보았다.
  - 결제 단계 설계 실패 여정(`designed_failure`, 하위 종류 `checkout`)의 품절·가격 변경을 따로 보지 않았다.

**방법**
- 스크립트: `eval/carttrace/carttrace_stockout_pick_decline.py`
- 결과 파일: `addendum1.json`
- 정규식은 셀 때 처음 정한 것이고 대략값이다. 첫 발화는 뺐다.
  - "고르기": go with, option N, I'd rather 등
  - "거절": not what I asked, don't place, stop the order 등. checkout·payment 단계의 턴만 센다.

**결과 (전체 split)**

| 묶음 | 여정 | 고르기 있음 | 결제 단계 거절 있음 | 고르기 → 거절 | 고르기 → 거절 (validation / test_cross_store / train) |
|---|---:|---:|---:|---:|---|
| 탐색 단계 품절(`intents.substitute`, 첫 발화에 조건부 대체) | 9,301 | 2,086 | 204 | 72 | 3 / 8 / 61 |
| 결제 단계 품절(설계 실패 `stockout`) | 101 | 46 | 17 | 11 | 3 / 1 / 7 |
| 결제 단계 가격 변경(설계 실패 `reprice`) | 96 | 34 | 10 | 3 | 0 / 0 / 3 |

- 탐색 단계 품절 72건의 결과: 결제 미완료·WRONG 53, 구매·RIGHT 12, 기타 7
- 결제 단계 품절 101건 중 91건은 `stopped_stock_gone`(품절로 멈춤)으로 끝났다.

**판단 (AI 1차)**
- 이 사례들은 대화 안에서 쇼핑객이 조건 변경처럼 보이는 선택을 했지만, 숨은 사양(정답)은 바뀌지 않은 경우다. 그래서 결제 단계에서 쇼핑객이 거절한다.
- 예를 들어 묶음 구매에서 한 품목만 고르는 답이 나오면, 에이전트는 이를 묶음 조건의 철회로 처리했다. 쇼핑객은 결제에서 "not what I asked for"라고 거절했다.
- 설계 v2의 M1 관점에서는 이것이 "모호한 고르기 발화를 필수 조건의 철회로 받아들인 경우"다. V3(완화·철회에는 명시적 근거 필요)가 pending으로 보내고, 결제 전에 CLARIFY해야 하는 사례에 해당한다.
- 쇼핑객 시뮬레이터의 최종 동의·거절은 사양에 따른 판정이다. 그래서 결제 확정 게이트의 자연스러운 정답으로 쓸 수 있다.
- 이 결과로 평가 초안의 제외 조건("designed_failure 제외")을 고쳐야 한다. 결제 단계 품절과 가격 변경 여정은 평가에 넣는다(설계 v2 §18).
- 한계: 정규식 집계다. 72건과 11건은 표본을 사람이 읽고 확인해야 한다.
