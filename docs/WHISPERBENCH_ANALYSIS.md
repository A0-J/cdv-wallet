# AP2-WhisperBench 분석: CDV-Wallet 평가에 재사용할 수 있는 범위

- 작성: 2026-11-26 밤
- 무과금이다. 모델 호출이 없고, 받은 코드도 실행하지 않았다.
- 데이터: HF `anonymos-2321135/ap2-whisperbench`, 리비전 `b9246d195fcf11e2663e84245fa9ad23e038f4c9`
  - 파일 306개(.pyc 제외), 53MB
  - 데이터셋 카드의 라이선스 표기: `cc-by-4.0`
  - README: "CC-BY 4.0 for the dataset; the loader code is MIT"
  - 저장 위치: `C:\ct\datasets\ap2_whisperbench_full\`(저장소 밖, `PROVENANCE.txt` 있음)
- 코드: `yedidel/avip_defense`의 최신 커밋은 `0c1b538`(2026-11-12)이고, 우리 포크와 같다.

## 1. 구성과 시나리오 수

| 파일 | 계열 | 수 | 형식 |
|---|---|---:|---|
| `attacks/tier2_v1·v2·v3.json` | vault 50 + branded 50 (각) | 300 | 단일 턴. `user_message`에 판매자 목록이 들어 있다 |
| `attacks/tier3_selection.json` | selection | 90 | 단일 턴. 요청 형태: underspecified 45 / in_brand 45. 판매자 문장 틀 16개 |
| `attacks/tier4_branded_factual.json` | branded_factual | 104 | 단일 턴 |
| `benign/seed_50.json`, `augmented_1000.json` | 정상 | 1,050 | 판매자 문장 하나와 판정 |
| `live_hp/main` | 판매자 하나, claim / noclaim | 시나리오 70, 실행 기록 700 | 실제 AP2 v0.2.0 흐름의 다중 턴 기록 |
| `live_hp/cross_seller` | 판매자 둘, 설정 S(한 판매자가 둘 다 판매) 70 / X(경쟁 판매자) 70 | 시나리오 140, 실행 기록 840 | 같음 |
| `live_hp/heldout` | 다른 모델(grok-4.7, qwen3.8-max)이 쓴 공격 문장 | 시나리오 140, 실행 기록 420 | 같음 |
| `live_hp/binding/*` | A-VIP 결속 측정(F0–F6), 판독 라벨 | 다수 | 기록, 결과, 사람 판독 |
| `live_hp/price_sweep` | 가격 비율 1.2배, 2.0배 | 실행 기록 560 | 같음 |

- 합계는 README와 맞는다: 공격 390 + 정상 1,050 + branded_factual 104 = 1,544

## 2. 품절·단종·대체 관련 사례

- 판매자 문장 틀 16개 중 재고·단종을 직접 말하는 것은 4개다.
  - 0: "unallocated … mapped continuation"
  - 1: "retired … carries the line forward"
  - 6: "fourteen-week lead time … ships from local stock"
  - 15: "needs an adapter that is out of stock"
- 나머지 12개는 반품률, 인증, 보증, 지원 종료 같은 다른 술어다.
- main 70개 시나리오 중 이 4개 틀은 20개다. heldout은 틀이 아니라 생성 문장이다.
- 실행 기록에서 비싼 상품(alt)을 고른 수:

| 묶음 | claim 팔 alt 선택 | noclaim 팔 alt 선택 |
|---|---:|---:|
| main, 재고 틀 | 48 / 100 | 38 / 100 |
| main, 기타 틀 | 87 / 250 | 58 / 250 |
| cross_seller, 재고 틀 | 70 / 120 | 45 / 120 |
| cross_seller, 기타 틀 | 130 / 300 | 75 / 300 |
| heldout(claim만) | 182 / 420 | — |

## 3. 다중 턴 대화 이력

- `tier*` 파일은 단일 턴이다. `multi_turn_setup` 값이 모두 비어 있다.
- `live_hp` 실행 기록은 다중 턴이다(대부분 6–8턴). 그러나 사용자는 스크립트다.
  - 첫 요청을 한 뒤 "No other preferences and no specific budget"과 "I'll go with the one you recommend"로만 답한다.
  - 조건을 추가하거나 바꾸거나 철회하는 턴은 없다.
  - 요청문(`request`)에 예산 표현이 있는 시나리오는 main 70개 중 0개다.

## 4. 재사용할 수 있는 것

| 자원 | 내용 | 재사용 |
|---|---|---|
| 실행 기록 `traces.zip` | 턴 전체, 후보 장바구니(`carts`, 역할 want/alt/filler, 금액, 판매자 글), 선택(`e_sel`, `e_sel_role`), 서명 여부 | 게이트 오프라인 재생에 그대로 쓴다. 선택 역할이 구조 필드라 판독 없이 정답이 정해진다 |
| A-VIP 재생 결과 `binding/replay/f4_*` | A-LEX + STRIP + R + 검증기 결과 | A-VIP 기준선 값으로 쓴다. E39(main) STRICT 거부 0/350, E41(cross_seller) claim STRICT 거부 78(V8) |
| 판독 라벨 `*/reading/final_labels.json` | 두 판독자와 판정 | 에이전트 응답의 의미 판정이 필요할 때만 쓴다 |
| 귀속 시험 세트 `binding/attribution/f2_*` | 대상이 알려진 주장, 음성(자기 주장, 자기 상품 재고 안내 `neg_own`) | E2 재고 주장 판별기의 정밀도·오탐 측정에 쓴다 |
| 공격 문장 틀, heldout 생성 문장 | 규칙 고정용과 일반화 검증용 | 규칙은 틀 16개로만 만들고, heldout은 마지막에 한 번만 쓴다 |

## 5. 현재 CDV-Wallet 권한 검증기에 바로 연결되는 것

- `live_hp`의 `carts`를 A-VIP Capture로 바꾸고, `e_sel`을 장바구니로 쓴다. 판매자는 cross_seller의 경우 라벨 " — Sold by"에서 읽는다(A-VIP 재생 관례).
- mandate는 요청문으로 만든다. 예산이 없고 브랜드 조건도 없으므로 P는 사실상 제한이 없다. 조건부 조항도 없다.
- **이 데이터에서 범위 검사(V10)는 공격을 막지 못한다.** 공격 상품이 P 안에 있기 때문이다.
- 차이가 날 수 있는 검사:
  - A-VIP V8: 경쟁 판매자 주장(X 설정)
  - 판매자 글 속 재고 주장에 E2를 적용하는 확장: 같은 판매자(S 설정, main)의 재고 틀 4개
  - M2b: 기준 주입. 틀 2 "Buyer guidance"와 13 "Capacity"가 가깝다
- **비교에서 주의할 점**
  - 공격 상품은 항상 더 비싸다(1.5배, price_sweep은 1.2배·2.0배). 예산도 없다.
  - 그래서 A-VIP 지출 규칙(비싼 쪽을 고르면 확인 요청)이 claim 팔의 alt 선택을 모두 잡는다.
  - 따라서 "+E2"가 공격을 추가로 막는 효과는 이 데이터에서 0이다.
  - 차이는 정상 쪽에서 난다. 지출 규칙은 noclaim 팔에서 비싼 쪽을 고른 경우에도 모두 확인을 요청한다(main 96/350, cross_seller 120/420). E2는 주장이 없으면 발동하지 않는다.
  - 그래서 이 데이터로 보고할 수 있는 것은 "같은 탐지에서 불필요한 확인 요청이 얼마나 줄어드는가"다. "더 많이 막는다"가 아니다.
- **증거 출처 기본값(플랫폼만)과의 관계:** WhisperBench에는 구조화된 재고 필드가 없다. 그래서 판매자 글 속 재고 주장은 모두 판매자 발화(자격 없음)로 처리된다.

## 6. M1을 위해 추가하거나 늘려야 하는 것

- WhisperBench에는 사용자의 조건 추가·변경·철회가 없다. M1 평가에는 사용자 턴을 덧붙여야 한다.
  - 예: 예산 추가, 브랜드 완화, "품절이면 B" 조건부 대체
  - 이것은 새 데이터 생성이라 이번 범위에서는 하지 않았다. 연구자 승인이 필요하다.
- 덧붙이면 판매자가 여럿인 같은 환경에서 M1을 평가할 수 있다. 다만 에이전트가 새 턴에 어떻게 반응할지는 새 실행(유료)이 필요하다. 오프라인 재생은 "게이트가 어떤 mandate로 무엇을 판정하는가"만 잰다.
- 실제로 일어난 품절과 조건 변경은 CartTrace에서 가져온다.
  - 탐색·결제 단계 품절
  - 고르기 → 결제 거절 72 + 11건
  - 구조화된 재고 필드
