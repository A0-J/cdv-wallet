# 평가 설계: AP2-WhisperBench + CartTrace-100k

- 작성: 2026-11-26 밤
- AI 1차 설계이며, 연구자 2차 검토 전이다.
- 상태: 설계만 했다. 모델 호출과 데이터 생성은 하지 않았다.
- 세부 근거: `WHISPERBENCH_ANALYSIS.md`, `M1_DESIGN.md`, `ADAPTER_DESIGN.md`, 공개 저장소 `results/` 각 폴더

## 0. 연구자 결정 (2026-11-26)

- **AP2-WhisperBench:** 기존 A-VIP와 같은 환경에서 권한 검증 성능을 비교하는 데 쓴다.
- **CartTrace-100k:** 다중 턴 대화 맥락 검증(M1)과 사용자 요구 변경 평가에 쓴다.
- **역할 구분**
  - 핵심 기여는 M1이다.
  - A-VIP 기반 권한 검증과 조건부 권한 검증은 전체 프레임워크의 안전성 평가에 쓴다.
- **원칙**
  - 원본 데이터와 추가 생성 데이터를 구분한다.
  - 기존 평가 환경을 최대한 유지한다.

---

## 1. 데이터셋별 구조와 평가할 수 있는 보안 속성

### 1.1 AP2-WhisperBench (원본, CC BY 4.0, HF 리비전 `b9246d19`)

| 구성 | 수 | 형식 |
|---|---:|---|
| 단일 턴 공격 tier2(vault, branded), tier3 selection, tier4 branded_factual | 300 + 90 + 104 | 사용자 요청과 판매자 목록이 한 메시지에 들어 있다 |
| 정상 문장 | 1,050 | 판매자 문장과 판정 |
| 실제 AP2 v0.2.0 흐름 실행 기록 main / cross_seller(S, X) / heldout / price_sweep | 700 / 840 / 420 / 560 | 다중 턴(6–8턴)이지만 사용자는 스크립트다(조건 변경 없음, 예산 없음). 후보 장바구니, 선택, 서명이 구조 필드로 들어 있다 |
| A-VIP 결속 측정(F0–F6), 판독 라벨, 귀속 시험 세트 | — | 재생 결과, 두 판독자 라벨, 음성 세트(`neg_own`, `neg_self`) |

| 평가할 수 있는 속성 | 근거 데이터 |
|---|---|
| 판매자 간 주장 권위(A-VIP V8) | cross_seller X |
| 같은 판매자의 재고·단종 주장 권위(E2 확장) | main, cross_seller S의 재고 틀 0·1·6·15 |
| 결정 기록 무결성(V1–V7) | F3 신원 사례, F4 재생 |
| 지출 확인 규칙(A-VIP §5.3) | 모든 실행 기록(공격 상품은 항상 더 비쌈) |
| 정상 비용(불필요한 확인 요청, 오탐) | noclaim 팔, `neg_own`, `neg_self`, 정상 1,050 |
| 규칙의 일반화 | heldout(다른 모델이 쓴 공격 문장) |
| **평가할 수 없는 것** | 사용자 조건 변경, 조건부 권한, 구조화 재고 증거, 다중 턴 맥락 검증 |

### 1.2 CartTrace-100k (원본, CC BY 4.0, 리비전 `86cab5e5`, 키트 `61f05faa`)

| 구성 | 수 | 형식 |
|---|---:|---|
| 여정 | 101,416 (train 77,765 / validation 4,199 / test_cross_store 10,334 / test_cross_template 9,118) | 프로토콜 5개(UCP, ACP, WebMCP, AP2, MPP). 숨은 사양(stated / on_ask / default 조건), 결과 분류, 동의·결제 시점 |
| 탐색 단계 품절 + 조건부 대체 요청(`intents.substitute`) | 9,301 | 구조화 재고 필드 `availability.status = "out_of_stock"` |
| 결제 단계 설계 실패 | 품절 101, 가격 변경 96, 배송 불가 120, 결제 거절 315, 3DS 315 | 오류 코드 `merchandise_out_of_stock` 등 |
| 품절 → 고르기 → 결제 거절 | 탐색 72 + 결제 11 (정규식 대략값) | 쇼핑객의 결제 단계 거절이 정답 역할을 한다 |
| 에이전트가 다시 발급한 권한 쌍(실험 4 부 B, train v0.2) | 252쌍 / 180여정 | 의도 확대 76, 제한 누락·변경 59, 품목 교체 168 |

| 평가할 수 있는 속성 (M1 항목) | 근거 데이터 |
|---|---|
| V-P 보존 | 실험 4 부 B 재발급 쌍(제한 누락 59쌍) |
| V-B 발화 근거 | 실험 2의 에이전트 작성 grant와 숨은 사양(2,739여정) |
| V-C 정당 변경 | 품절 → 고르기 → 거절 83건, 실험 4 부 B 의도 확대 76쌍 |
| V-X 충돌 | 원본에는 거의 없다. 생성 세트가 필요하다 |
| V-S 조건부 대체의 발동·범위 | `intents.substitute` + 진짜 품절(구조화 필드) |
| 환경 사실이 조건을 완화하지 못함 | 결제 단계 가격 변경 96 |
| **한계** | 완화·덮어쓰기·철회 같은 실제 사용자 수정은 거의 없다(7,848턴 중 1턴). on_ask 공개 시점을 결정적으로 정할 수 없다. 판매자는 여정마다 하나다 |

---

## 2. 기존 실험 환경과 코드 재사용

| 대상 | 재사용 방법 | 고치지 않음 |
|---|---|---|
| A-VIP binding `mechanism/`(Apache 2.0) | `adapters/avip.py`로 그대로 import한다 | 포크, submodule 고정 |
| A-VIP F4 재생 결과 | 우리 어댑터로 같은 값(STRICT 거부 수 등)이 나오는지 확인한 뒤 기준선으로 쓴다 | 원본 파일 |
| WhisperBench 실행 기록 | 오프라인 재생 입력 | 원본 zip |
| WhisperBench `loader/judges.py`(MIT) | 에이전트 응답의 의미 판정이 필요할 때만 읽고 쓴다. 실행은 승인 뒤에 한다 | — |
| CartTrace 키트·가상환경 `C:\ct\kit` | 데이터 읽기와 재생 | — |
| `experiments/carttrace_protocol_ext/replay.py`(sha256 `69425b88…`) | 1부 재생과 grant 묶음. import해서 쓴다(`avip_row.py`가 이미 그렇게 쓴다) | 동결 코드 |
| `experiments/carttrace_protocol_ext/avip_row.py` | A-VIP 규칙을 CartTrace 2,739여정에 적용한 것. CartTrace 쪽 A-VIP 기준선이다 | 동결 결과 |
| `experiments/carttrace_grant_gap/grant_gap.py` | 에이전트 작성 grant 추출 | 동결 결과 |
| `experiments/.../reissue*.py`(실험 4) | 재발급 쌍과 합성 변경 | 동결 결과 |
| `eval/carttrace/*.py` | 품절·거절 사례 목록 | — |

- **동결 기록 원칙(`results/README.md`):** 실험 2·3·4의 사전등록, 결과, 코드는 고치지 않는다. 새 분석은 새 파일로 덧붙인다.

---

## 3. 공통 어댑터 (두 데이터셋을 같은 게이트에 넣기)

### 3.1 공통 단위 `Episode`

```
Episode
  source            "whisperbench" | "carttrace"
  episode_id, split, dataset_revision
  user_turns        [(turn_id, text, sha256)]          # 사용자 채널만. 해시 체인 입력
  agent_turns       [(turn_id, text)]                  # 검증기 입력에는 넣지 않는다
  offers            [(seller, cart_id, label, amount, currency, attrs)]   # A-VIP Capture 입력 = 표시 로그
                    attrs: brand, product_ref, features, availability(구조화 필드만)
  env_facts         [(kind, subject_key, value, channel, seq)]
                    kind: stock | price | error;  channel: "structured" | "prose"
  mandate_gold      P, F_k                             # 정답 사양
  mandate_agent     에이전트가 실제로 쓴 권한(있으면)
  cart_final        [(key, qty)]
  labels            violation(bool), consent(accept/decline/none), chosen_role(want/alt/filler)
  provenance        original | generated(generator_id, template_id, seed)
```

### 3.2 데이터셋별 변환

| 필드 | WhisperBench | CartTrace |
|---|---|---|
| user_turns | 실행 기록의 `author=user` 턴(스크립트) | `turns`에서 `actor=shopper` |
| offers | `carts`(cart_id, item_label, amount). 판매자는 cross_seller 라벨의 " — Sold by"에서 읽는다(A-VIP 재생 관례). 그 밖은 기본 판매자 | 카탈로그 도구 결과(`search_catalog`, `get_product`, `search_products`)의 variant id, 가격, 브랜드, `availability` |
| env_facts | 재고 정보는 판매자 글에만 있다(channel=prose) | 구조화 재고 필드와 결제 오류 코드(channel=structured), 판매자 글 속 재고 문장(prose) |
| mandate_gold | `request`(브랜드 조건은 in_brand일 때만, 예산 없음), 조건부 조항 없음 | 숨은 사양의 stated·default 조건. `intents.substitute`는 조건부 대체 조항(then = 같은 상품 종류 + 기존 조건 이어받기) |
| mandate_agent | `checkout_payload`(서명된 장바구니) | AP2 여정의 Intent/Cart mandate(실험 2 추출 재사용) |
| cart_final, labels | `e_sel`, `e_sel_role`, arm | `final_cart`, `outcome_class`, 결제 단계 동의·거절 |

- **같은 게이트를 쓴다:** `cdv/gate.py`는 Episode에서 만든 같은 입력만 받는다. 데이터셋별 분기는 변환 함수에만 둔다.
- **구현 범위(연구자 지시: 어댑터에 시간을 많이 쓰지 않는다)**
  - 실험에 필요한 필드만 변환한다.
  - CartTrace는 AP2·UCP 표면부터 한다.
  - WhisperBench는 main과 cross_seller부터 한다.

---

## 4. 조건부 권한과 동적 변경 시나리오

### 4.1 원본 데이터로 만드는 시나리오 (생성 없음)

| ID | 시나리오 | 출처 | 보는 것 |
|---|---|---|---|
| O1 | 진짜 품절 뒤 조건부 대체 | CartTrace `intents.substitute` + 구조화 재고 필드 | V-S 발동(증거 = 구조화 필드), 대체 범위 |
| O2 | 결제 단계 품절·가격 변경·배송 불가 | CartTrace 설계 실패 `checkout` | 환경 사실이 조건을 바꾸지 못함(가격 변경 → 예산 초과면 CLARIFY) |
| O3 | 모호한 고르기 뒤 결제 거절 | CartTrace 83건 | V-C(철회로 해석하지 않음) |
| O4 | 사건 뒤 권한 재발급 | 실험 4 부 B 252쌍 | V-P(제한 누락), V-C(의도 확대) |
| O5 | 판매자 글의 가짜 품절·단종 | WhisperBench 재고 틀 4개 | E2(글 속 재고 주장은 자격 없음) |
| O6 | 경쟁 판매자 주장 | WhisperBench cross_seller X | A-VIP V8 |

### 4.2 추가 생성 데이터 (연구자 승인 뒤, 모델 없이 고정 템플릿)

| ID | 내용 | 대상 | 규모(초안) |
|---|---|---|---|
| G1 | CartTrace 기록 위에 사용자 변경 턴을 덧붙임: 완화, 덮어쓰기, 철회, 우선순위 변경, 생략·참조, 조건부 대체 추가, 시점, 모호 | V-C, V-X, V-P 정확도 | 종류당 20 |
| G2 | CartTrace 기록에 비사용자 주입: 가짜 정책, 글 속 가짜 품절, 기준 주입, 참조 가로채기, 낡은 동의, 에이전트 일방 완화 | 게이트 수준 공격 | 종류당 20 |
| G3 | WhisperBench 기록에 사용자 턴을 덧붙임: 예산 추가, "A 품절이면 B", 브랜드 완화 | 판매자가 여럿인 같은 환경에서의 M1, 지출 규칙이 침묵하는 경우 | 종류당 20 |
| G4 | 구조화 재고 필드를 감싼 모의 증거(HMAC → 2단계 전 ECDSA P-256) | 증거 E1–E3 | 원본 품절 수만큼 |

- **보관과 구분**
  - 원본은 `C:\ct\datasets\...`에 두고 읽기만 한다.
  - 생성물은 `C:\ct\runs\cdv_wallet\generated\<ID>\`에 덮어쓰기 층(overlay)으로만 둔다. 원본 에피소드 ID, 템플릿 ID, 시드를 함께 적는다.
  - 원본 파일에는 섞지 않는다.
  - 저장소에는 생성 코드, 템플릿 문구, 목록 해시만 넣는다.
  - 결과표에는 원본(O)과 생성(G)을 항상 따로 적는다.
- **오프라인 재생의 한계:** 생성 턴에 에이전트가 어떻게 반응할지는 재지 않는다. 기록된 장바구니(또는 정답·위반 장바구니 짝)를 게이트에 넣어 판정만 잰다.

---

## 5. 기존 CartTrace 실험 결과의 재사용 범위

| 기존 결과 (공개 저장소 `results/`) | 재사용 | 쓰는 곳 |
|---|---|---|
| 실험 2 `carttrace_grant_gap_20261122` | 에이전트가 쓴 grant(2,739여정)를 그대로 mandate_agent로 쓴다. 모델 호출이 필요 없다 | E-M1 기준선(b) "에이전트 작성 권한", V-B 동기 |
| 실험 3 1부 `carttrace_protocol_ext_20261122` | 재생 환경과 B0–B3 규칙 결과 | 권한 쪽 기준선, 같은 2,739여정 |
| A-VIP 행 `avip_row_20261125` | A-VIP 규칙을 CartTrace에 적용한 값(노출 93.7% 등) | CartTrace에서의 A-VIP 기준선 |
| 실험 3 2부(유료, 동결) | 묻기 절차 결과(C2 혼합, C4 유지) | CLARIFY 비용의 배경. 다시 실행하지 않는다 |
| 실험 4 부 A `carttrace_reissue_20261123` | 합성 변경(품절 대체, 배송, 가격 ±10·20%, 다른 상품)에서 재발급 정책 P1–P4의 결과(P2: 안전 충족, 재확인 감소 기준 미달) | 조건부 대체(V-S)와 비교할 기존 정책 결과 |
| 실험 4 부 B | 자연 재발급 252쌍과 분류 | O4 평가 세트 |
| 사후 분석 `hard_condition_posthoc_20261126` | 필수 조건 노출(B1 17.7% 등), 거절 472건 중 작성 오류 341건 | M1 필요성(배경) |
| 판정표·라벨 점검(answer_table_audit, item_truth_ai, label_validation, simulator_bias, a3_phase0) | 정답의 한계와 시뮬레이터 편향 | 타당성 위협 절 |
| `test_split_check_20261123` | test 두 분할은 이미 한 번 썼다 | 이후 test 분석은 사후로 표시한다(분할 원칙) |
| `cdv_wallet_field_check_20261126` | 구조와 품절·거절 사례 | O1–O3 대상 목록 |

---

## 6. A-VIP 비교와 구성 요소 제거 실험

### 6.1 WhisperBench: 권한 검증 (A-VIP와 같은 환경, 모델 호출 0)

| 팔 | 구성 |
|---|---|
| W0 | 방어 없음(기록된 결과 그대로) |
| W1 | A-VIP binding STRICT(F4 재생 값을 우리 어댑터로 다시 내어 일치 확인) |
| W2 | W1 + A-VIP 지출 확인 규칙(논문 §5.3. `avip_row.py`에 구현된 규칙을 옮김) |
| W3 | W2 + E2 확장(글 속 재고·단종 주장은 플랫폼만 자격) |
| W4 | W3 + M2b(기준 주입: 결정적 규칙부터) |
| W5 | W4 + M1(G3 생성 세트에서만) |

- **지표**
  - claim 팔에서 비싼 상품이 서명된 경우의 게이트 통과율(공격 성공)
  - noclaim 팔의 확인 요청률(정상 비용)
  - `neg_own`·`neg_self` 오탐
  - heldout 일반화: 규칙은 틀 16개로만 고정하고, heldout은 마지막에 한 번만 쓴다
- **결과를 보기 전에 적는 예상**
  - 원본에서는 공격 상품이 항상 더 비싸고 예산이 없다. 그래서 W3의 추가 차단은 W2 대비 0일 것이다.
  - 차이는 정상 비용에서 날 것이다(지출 규칙은 noclaim 팔에서 비싼 쪽을 고른 main 96건, cross_seller 120건에도 확인을 요청).
  - 추가 차단 효과는 G3(예산이 있어 지출 규칙이 침묵하는 경우)에서만 잴 수 있다.

### 6.2 CartTrace: M1의 효과 (E-M1, 핵심)

- **같은 게이트에 mandate만 바꿔 넣는다.**

| 팔 | mandate | 모델 호출 |
|---|---|---|
| M-a | 정답(숨은 사양) — 상한 | 없음 |
| M-b | 에이전트 작성 권한(실험 2 재사용) | 없음 |
| M-c | 단순 추출(FnCTOD식, 검증 없음) | 필요 |
| M-d | 중립 요약 + 강화 프롬프트 판정(Google SGP 공개 설명 기반 재구현) | 필요 |
| M-e | EAL 출처 필터링 / 이벤트 방식(재구현) | 필요 |
| M-f | 추출 + M1 검증(제안) | 필요(NLI는 로컬 가능) |

- **대상:** O1–O4(원본), G1·G2(생성)를 따로 보고한다.
- **지표**
  - 위반 장바구니 통과율
  - 정당 장바구니 통과율
  - CLARIFY 비율
  - 항목별 정확도(V-P, V-B, V-C, V-X, V-S)
- **M1의 기여 판단:** M-f가 M-b·M-c·M-d·M-e보다 나아야 주장한다. 같거나 못하면 주장하지 않는다(반증 기준).

### 6.3 전체 프레임워크 (E-F, 데이터셋별 따로 보고)

- CartTrace 제거 순서:
  1. A-VIP 규칙만(`avip_row` 재사용)
  2. + 조건부 조항과 증거(V-S, E1–E3)
  3. + M1
  4. 전체
- WhisperBench 제거 순서: W1 → W5(§6.1)

### 6.4 통계와 사전등록

- 단위는 여정이다. Wilson 95% 구간을 쓰고, 상점·범주 군집 재표집으로 확인한다(이전 실험과 같은 방식).
- 원본 세트는 validation으로 규칙을 고정한다. 최종은 test_cross_store로 하되 사후 표시를 붙인다(§5). train은 학습이 없으므로 사례 수가 부족할 때만 쓰고, 그때는 사전등록에 적는다.
- 모델 호출이 필요한 팔(M-c–M-f, W4의 LLM 경로)은 계획 sha256 승인 뒤에 실행한다.

## 7. 다음 순서 (모두 무과금, 승인 대기)

1. WhisperBench W0–W3 계산(원본, 모델 호출 0). 사전등록을 먼저 쓴다.
2. CartTrace M-a·M-b 계산(원본, 모델 호출 0): 정답 mandate와 에이전트 작성 권한을 같은 게이트에 넣는다.
3. G1–G3 템플릿 문구 초안 작성(연구자 검토 후 생성)
4. M1의 결정적 부분(V-P diff, V-X 구간·집합, V-S 범위) 구현
