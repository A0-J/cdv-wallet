# 권한 검증 어댑터 설계 (A-VIP binding, Standing)

- 작성: 2026-11-26 밤
- AI 1차 설계이며, 연구자 2차 검토 전이다.
- 상태: 설계만 했다. 구현, 시험 실행, 모델 호출은 하지 않았다.
- 대상: Fig. 1의 Standing Verification(§4.3), Context-bound Signed Mandate(§4.4), Authorization Verification(§4.5)
- 읽은 코드(복제본만 읽고 실행하지 않음):

| 포크 | 커밋 | 라이선스 | 읽은 범위 |
|---|---|---|---|
| A0-J/avip_defense (← yedidel/avip_defense) | `0c1b5388de1ea022a99b0f96f662d1b277bec313` (2026-11-12) | Apache 2.0 | `binding/README.md`, `binding/mechanism/*.py` 전부 |
| A0-J/standing-not-truth (← yedidel/standing-not-truth) | `9f041c08813c01edd1cfc90886193f16717f88db` (2026-11-25) | 코드 MIT(데이터는 별도) | `README.md`, `A7_standing_classifier/classifier.py`, `A13_field_consistency/field_check.py`, `B19`, `B20_commerce_domain/run.py` 일부 |

---

## 1. 두 코드의 성격 (확인한 사실)

### 1.1 A-VIP binding (`binding/mechanism/`)
- 라이브러리로 쓸 수 있다.
  - 표준 라이브러리만 쓴다(hashlib, json, re, dataclasses).
  - 네트워크와 모델을 호출하지 않는다("Nothing in this package calls an LLM or the network").
- 공개 API(`__init__.py`):
  - `build_capture`, `Capture`, `Offer`, `offer_key`
  - `ALex`(코드 전용 귀속기), `ALLMStub`(LLM 요청 생성과 응답 파싱만 함)
  - `attribute_and_rule`, `apply_policy`(STRIP / ANNOTATE)
  - `build_record`, `record_hash`, `canonical_json`
  - `verify(r, capture, mode="DEFAULT"|"STRICT", attributor=None) -> Verdict(ok, failures)`. 검사 코드는 V1–V8이다.
- 상품 식별자는 항상 (seller, cart_id)다. 제목은 식별자로 쓰지 않는다.
- 권위 규칙은 `seller(speaker) == seller(target)` 하나다. 같은 제목의 다른 판매자 상품으로 대상을 확장해서 복제 상품 우회를 막는다.
- 결정 기록 R에는 다음이 들어간다: 후보 다이제스트, 보여 준 글 다이제스트, 정책, 귀속기, 선택 상품 키, 주장 목록, `user_confirmed`.

### 1.2 Standing (`standing-not-truth/experiments/`)
- 라이브러리가 아니라 실험 스크립트 모음이다. 대부분 저장된 응답을 다시 읽어 수치를 계산한다.
- 권위 규칙 `admissible(s,u,p,v) = s = u ∨ s ∈ AUTHORITY(p)`를 함수 하나로 구현한 곳은 없다. 규칙은 논문에 정의돼 있고, 실험마다 판정 결과를 저장해 쓴다.
- 가져다 쓸 수 있는 부품:
  - `A7_standing_classifier/classifier.py`의 `lexical_classify`: 결정적이고, re와 dataclasses만 쓴다. 다른 상품을 지칭하는 문장 + 상태 술어가 있으면 "third"로 판정한다.
  - `B20_commerce_domain/run.py`의 `SUBJECT_PROMPT`: 상거래용 주어 판별 LLM 프롬프트다. 응답은 ASSERTS / MENTIONS다.
  - `A13_field_consistency/field_check.py`: 기록값과 글의 일치 검사다. npm 전용 필드(last_publish 등)라 상거래에는 그대로 쓸 수 없다.
- 실험 스크립트는 import할 때 하네스를 불러오는 부작용이 있다. 그래서 import하지 않는다.

---

## 2. 원칙

1. **포크는 고치지 않는다.** 커밋을 고정한 submodule(`third_party/`)로만 가져온다.
2. **A-VIP는 import해서 그대로 쓴다.** 우리 쪽 필드는 A-VIP의 R에 넣지 않고 별도 기록으로 둔다. 그래야 A-VIP의 V1·V6 다이제스트 검사가 깨지지 않는다.
3. **Standing은 규칙을 다시 구현한다.** 규칙이 한 줄이라 그렇다. 부품(lexical 분류기, 주어 프롬프트)은 문자열과 함수를 옮겨 오고, 원본과 같은지 시험으로 확인한다. 시험은 고정 커밋의 파일을 ast로 읽어 비교한다. MIT 표기는 `NOTICE`에 적는다.
4. **어댑터는 얇게 만든다.** 판정 논리는 `cdv/`에 두고, 어댑터는 자료형 변환만 한다.
5. **모델을 호출하는 경로는 기본으로 꺼 둔다.** 기본값은 ALex와 lexical이다. LLM 경로(ALLMStub, SUBJECT_PROMPT)는 승인된 계획(sha256) 아래에서만 켠다.

---

## 3. 구성

```
cdv/
  ledger.py        조건 장부 C_t (항목, 버전, 상태, 근거 발화)
  change.py        M1 변경 검증 V1–V5, 선택 반영, 보존, 대기
  clause.py        조건부 대체 조항(fallback)과 발동 판정
  evidence.py      증거 3단계 검증(출처·권위·조건)
  gate.py          결제 확정 게이트: ALLOW / CLARIFY / DENY + 사유 코드
  binding.py       맥락 기록 C_R, 결합 해시, 확장 검증 V9–V12
adapters/
  avip.py          CartTrace·하네스 자료 → A-VIP Capture/R, verify 호출
  standing.py      admissible 규칙, AUTHORITY 표, lexical·LLM 주어 판별
third_party/
  avip_defense/          submodule @0c1b538
  standing-not-truth/    submodule @9f041c0
```

---

## 4. A-VIP 어댑터 (`adapters/avip.py`)

### 4.1 입력 변환
- **후보 → Capture:** `build_capture([{cart_id, seller, label, amount, currency}])`
  - `cart_id`: CartTrace의 `variant_id`
  - `seller`: 상점 식별자(`store_id`). S3에서 넣는 경쟁 판매자 상품에는 별도 seller ID를 준다.
  - `label`: 에이전트가 본 글 그대로(제목 + 설명)
  - `amount`: 단가. 통화 단위는 CartTrace의 정수 센트를 소수로 바꾼다.
- **CartTrace의 한계:** 여정 하나에 상점이 하나라 실제 데이터에는 경쟁 판매자가 없다. 판매자 간 주장은 모두 S3 주입으로 만든다. 그러면 A-VIP 권위 규칙(seller 비교)이 S3 경쟁 판매자 사례에서만 작동한다.
- **도구 결과 파싱:** CartTrace 도구 결과는 프로토콜(UCP, ACP, AP2, MPP, WebMCP)마다 형식이 다르다. 파서를 프로토콜별로 두어야 한다. 아직 형식을 확인하지 않았다(§9 확인 항목).

### 4.2 표시 로그로 재사용
- Capture는 "에이전트가 받은 후보 전체"의 다이제스트다. 그래서 M1 V4(참조 검사)의 표시 로그로 그대로 쓴다.
- 참조 대상은 Capture 키여야 한다. 판매자 글이 지칭한 "그 모델"이 Capture에 없으면 참조할 수 없다.
- 주의: A-VIP Capture는 "받은 것"이다. 사용자 화면에 "보여 준 것"과는 다를 수 있다. 사용자에게 보여 준 목록은 에이전트 메시지에서 따로 뽑아야 하는데, 이 작업은 LLM이나 규칙이 필요하다. 1차 구현은 받은 것 = 보여 준 것으로 가정하고, 그 가정을 논문에 적는다.

### 4.3 결정 기록과 맥락 기록의 결합
- A-VIP R은 그대로 만든다: `build_record(capture, claims, chosen_key, policy, "A-LEX v1", user_confirmed)`
- 우리 쪽 맥락 기록 C_R(별도 dict)의 필드:
  - `ledger_hash`, `ledger_version`
  - `pending_resolved`(CLARIFY 결과)
  - `clause_id`(발동한 조건부 조항, 없으면 null)
  - `evidence_ids`
  - `user_turn_chain_head`(사용자 발화 해시 체인의 끝값)
- 결합 해시: `H = SHA-256(canonical_json({"avip_r": record_hash(R), "cdv": C_R}))`
  - A-VIP의 `canonical_json` 규칙(sort_keys, 구분자, UTF-8)을 그대로 쓴다.
  - H를 체크아웃·결제 mandate에 결속한다(M3).

### 4.4 검증 순서 (Authorization Verification, §4.5)

1. **A-VIP 검사:** `verify(R, capture, mode="STRICT", attributor=ALex())`. V1–V8 중 하나라도 실패하면 DENY다.
2. **확장 검사(우리 코드, `cdv/binding.py`)**

| 코드 | 검사 | 실패하면 |
|---|---|---|
| V9 버전 | C_R.ledger_version이 최신이고 폐기되지 않았는가. 서명된 G의 버전 v와 같은가 | DENY(폐기된 권한) 또는 CLARIFY(새 버전 서명 필요) |
| V10 범위 | 장바구니 a가 S_active 안에 있는가(§6). 상품, 수량, 가격, 판매자를 본다 | 미리 말하지 않은 변경이면 CLARIFY, 명백한 위반이면 DENY |
| V11 증거 | 조항이 발동했다면 그 증거가 §5의 세 단계를 모두 통과했는가 | 조항을 발동하지 않음 → 기본 범위 P로 V10을 다시 판정 |
| V12 결합 | mandate에 묶인 H가 R과 C_R로 다시 계산한 값과 같은가 | DENY |

---

## 5. 증거 3단계 검증 (`cdv/evidence.py`, Standing 어댑터 사용)

- 대상: 조건부 조항을 여는 사실이다. 1차 범위는 품절이고, 가격 변경으로 확장할 수 있다.

| 단계 | 질문 | 방법 | 비고 |
|---|---|---|---|
| E1 출처 | 증거가 정말 지정된 발급자가 만든 것인가 | 서명 검증 | 실험 하네스에서는 발급자별 키로 서명을 흉내 낸다(HMAC-SHA256 또는 Ed25519). 실제 서명 재고 API가 있다고 주장하지 않는다 |
| E2 권위 | 그 발급자가 그 상품의 재고를 말할 자격이 있는가 | `admissible(s=issuer, u=subject_seller, p="stock")` = s = u ∨ s ∈ AUTHORITY("stock") | AUTHORITY("stock") = {platform}. 판매자 자신(s = u)은 규칙에 따라 항상 통과한다 |
| E3 조건 | 증거가 조항과 맞는가 | 결정적 규칙 | 대상 상품(조항의 when.subject와 같은 키), 판매자 범위(when.scope), 시각(TTL 안), nonce(세션에 묶이고 처음 쓰는 것) |

**Standing 규칙 구현 (`adapters/standing.py`)**
```python
AUTHORITY = {
    "stock": {"platform"},         # 판매자 자신은 s == u로 통과
    "price": {"platform"},
    "policy_update": {"platform"}, # 상점 정책 변경. 자유 글은 해당 없음
    "criteria": set(),             # 판단 기준: 환경에는 권위 없음(M2b)
}
def admissible(speaker, subject_owner, predicate):
    return speaker == subject_owner or speaker in AUTHORITY.get(predicate, set())
```

- 이 규칙은 A-VIP `authority.py`의 `seller(speaker) == seller(target)`를 술어별 권위로 넓힌 것이다(Standing 논문의 정의).
- 판매자 글에서 주어를 판별할 때:
  - 기본값: `lexical_classify`(Standing A7)
  - 선택: `SUBJECT_PROMPT`(Standing B20, LLM, 승인 필요)
- **같은 판매자가 두 상품을 모두 파는 경우의 한계**
  - 판매자 X가 "우리 저가 모델은 품절, 고가 모델을 사세요"라고 말하면 s = u라서 E2를 통과한다.
  - 이 경우 막는 것은 출처 검사가 아니다. 막는 장치는 다음 두 가지다.
    - (a) 조항의 then 범위: 가격 상한과 필수 조건
    - (b) 조항의 proof에 판매자 자신을 넣을지 여부. 높은 신뢰가 필요하면 proof를 {platform}만으로 둔다.
  - 그래도 사용자가 원하지 않는 대체 자체는 막지 못할 수 있다. 이 점을 한계로 적는다.

---

## 6. 조건부 대체 조항과 실행 범위 (`cdv/clause.py`)

### 6.1 조항 형식 (설명용 예시이고, AP2 필드가 아니다)
```json
{
  "primary":  {"brand": "Sony", "max_price": 300000, "required": ["ANC"]},
  "fallback": [{
    "id": "fb-1",
    "when":  {"subject": {"seller": "S1", "cart_id": "sony-wh"}, "predicate": "out_of_stock",
              "scope": "subject_seller"},
    "proof": ["platform"],
    "ttl_s": 600,
    "then":  {"brand": "Bose", "max_price": 300000, "required": ["ANC"]}
  }],
  "basis": {"fb-1": ["user_turn:2"]},
  "version": 3
}
```
- `scope`는 품절을 어느 판매자 집합 기준으로 보는지 정한다(`subject_seller` / `all_captured_sellers`). 이 필드가 없으면 품절인 판매자 한 곳만 찾아도 조항이 열린다.
- `basis`는 M1이 검증하는 대상이다. 그 발화가 정말 이 조항을 의미하는지 본다.
- 조항은 권한 범위를 넓힌다. 그래서 사용자가 읽을 수 있는 문장으로 보여 주고 서명받는다(§16.3의 "범위가 넓어질 때만 서명").

### 6.2 실행 범위 (연구자 쪽 AI의 정식화를 고친 것)
- 제안된 식은 `S_active = F (V_E = 1) / P (그 외)`였다.
- 문제가 두 가지 있다.
  - 품절 증거가 있으면 P가 범위에서 빠진다.
  - 증거가 판매자 한 곳 기준인데, 다른 판매자에게 기본 상품이 있으면 P로 사는 것이 맞다.
- 고친 식:

```
S_active = P ∪ { F_k : V_E(e_k, T_k, E_k) = 1 }
Allow(a) = V_avip(R) ∧ V_ver(v) ∧ V_bind(H) ∧ (a ∈ S_active) ∧ V_ctx(C_t)
Prefer   : a ∈ P 이면 P를 우선하고, F_k는 P 안에 선택지가 없을 때만 쓴다(사용자 발화의 "이면"을 따름)
```
- `V_ver`: 서명된 버전이 최신이고 폐기되지 않았는가. 원래 식에는 이 항이 없어서 이전 권한으로 결제하는 시도를 막지 못한다.
- `V_ctx`: M1 장부의 현재 활성 조건을 만족하는가.
- 성질: `S_active ⊆ P ∪ ⋃F_k ⊆ 서명된 범위`. 조항이 발동해도 서명 밖으로 넓어지지 않는다.
  - 다만 이 성질은 능력(capability) 기반 설계라면 일반적으로 갖는 것이다. 신규성으로 주장하지 않는다.
- h_C(맥락 해시)에는 사용자 채널 발화의 해시 체인만 넣는다. 판매자 글은 넣지 않는다(§16.3).

---

## 7. 게이트 판정 (`cdv/gate.py`)

| 상황 | 판정 | 사유 코드 |
|---|---|---|
| a ∈ P, 모든 검사 통과 | ALLOW | — |
| a ∈ F_k, 증거 E1–E3 통과 | ALLOW | CLAUSE_ACTIVE |
| a ∈ F_k, 증거가 없거나 실패 | CLARIFY | EVIDENCE_MISSING / EVIDENCE_REJECTED_E1·E2·E3 |
| a ∉ P ∪ F, 결정이 대기 변경에 기댐 | CLARIFY | PENDING_CHANGE |
| a ∉ P ∪ F, 근거 있는 변경 없음 | DENY | OUT_OF_SCOPE |
| V9 폐기 버전 | DENY | STALE_VERSION |
| A-VIP V1–V8 실패, V12 실패 | DENY | AVIP_Vn / BIND_MISMATCH |

- 증거가 없어서 CLARIFY로 떨어지는 비율은 따로 보고한다. 서명 재고 출처가 실제로 없을 때 생기는 사용자 부담이다.

---

## 8. 시험 계획 (모델 호출 없이, 구현 뒤)

- A-VIP 자체 시험: `third_party/avip_defense/binding/tests`를 실행해 고정 커밋이 원래대로 동작하는지 확인한다.
- 원본 일치 시험: 옮겨 온 `lexical_classify`, `SUBJECT_PROMPT`가 고정 커밋 파일과 같은지 ast로 비교한다.
- 시나리오 시험(연구자 쪽 AI가 제안한 8개 + 보완):
  1. 정상 구매: a ∈ P → ALLOW
  2. 진짜 품절 뒤 대체: 플랫폼 서명 증거 → ALLOW(CLAUSE_ACTIVE)
  3. 경쟁 판매자의 거짓 품절 주장: E2 실패 → 조항 미발동 → 대체 장바구니 CLARIFY 또는 DENY
  4. 위조된 재고 증거: E1 실패
  5. 과거 재고 증거 재사용: E3(TTL, nonce) 실패
  6. 사용자가 대체 조건을 말하지 않음: 조항 없음 → OUT_OF_SCOPE
  7. 사용자 예산 변경: 새 버전 서명 → 새 범위로 ALLOW
  8. 이전 버전으로 결제 시도: STALE_VERSION
  9. (보완) 같은 판매자의 자기 품절 주장 + 고가 대체: proof={platform}이면 CLARIFY, proof에 판매자가 있으면 then 상한 안에서 ALLOW. 이것이 한계 사례다.
  10. (보완) 판매자 한 곳만 품절, 다른 판매자에게 재고 있음: scope=all_captured_sellers이면 조항 미발동, 기본 상품 우선
  11. (보완) A-VIP 결정 기록 변조: V12/V1 실패

---

## 9. 구현 전에 확인할 것

1. CartTrace 도구 결과의 프로토콜별 형식: 후보 목록, 재고, 가격 필드를 어디서 읽는지
2. CartTrace 품절이 도구 결과에 어떻게 나타나는지: 구조화 필드인지, 오류 코드인지, 글인지. 하네스가 "플랫폼 서명 증거"로 감쌀 원천이 무엇인지
3. A-VIP Capture의 "받은 것 = 보여 준 것" 가정을 어디까지 받아들일지
4. 증거 서명 흉내 방식: HMAC은 표준 라이브러리, Ed25519는 `cryptography` 필요

## 10. 신규성 경계 (설계에서 주장하지 않는 것)

- 조건부 권한과 증거 기반 발동 자체: XACML·ABAC의 환경 속성 조건과 같은 계열이다.
- 결정 기록 결속, 권위 규칙: A-VIP와 Standing이 원저작이다.
- 차별점으로 두는 것은 다음 두 가지다(설계 v2 §0의 연구자 결정과 같음).
  - 다중 턴 대화에서 조항의 근거(basis)와 변경을 M1로 검증하는 것
  - 그 결과를 증거 발동과 결제 집행까지 한 경로로 잇는 것

---

## 11. 확정 (2026-11-26 밤, 연구자 결정)

### 11.1 A-VIP와 Standing의 역할
- **A-VIP binding이 권한 검증의 기반이다.** 다음을 그대로 쓴다.
  - Capture
  - 판매자 간 주장 귀속(A-LEX)과 판매자 비교 권위 규칙
  - 결정 기록 R
  - 검증기 V1–V8
- **Standing 규칙(s = u ∨ s ∈ AUTHORITY(p))은 두 곳에만 적용한다.**
  - (a) 증거 권위 E2: AUTHORITY(stock) = {platform}
  - (b) 판단 기준 권위 M2b: AUTHORITY(criteria) = ∅
- **판매자 글의 남에 대한 주장 검사는 A-VIP로만 한다.** Standing 판별기로 다시 돌리지 않는다.
  - 기본값은 A-LEX다.
  - Standing의 LLM 주어 판별(SUBJECT_PROMPT)은 승인 뒤 비교용으로만 쓴다.
- **논문 서술 원칙:** "A-VIP binding으로 결정과 결제를 결속하고, Standing의 술어별 권위 규칙을 증거와 판단 기준으로 넓혔다." 두 기술을 함께 쓴 것 자체를 기여로 쓰지 않는다.

### 11.2 Fig. 1 수정안
- 별도 상자였던 Standing Verification(§4.3)을 Authorization Verification 안의 하위 단계로 넣는다.

```
[Authorization Verification (§4.5)]
  ├─ (a) A-VIP binding check (existing): capture, cross-seller claim authority, decision record, V1–V8
  ├─ (b) Evidence & criteria authority (Standing rule, extended): E1 source · E2 authority · E3 condition; criteria ∅
  └─ (c) Context binding (added): ledger version, active scope S_active, combined hash H (V9–V12)
```

- 색 구분:
  - (a)는 회색(기존 기술)
  - (b)는 초록(Standing 규칙의 확장)
  - (c)는 보라(제안)
- Merchant Information에서 나오는 화살표는 다음으로만 연결한다.
  - Authorization Verification의 (a)·(b)
  - 에이전트 결정
- Context State Tracking으로 가는 화살표는 지운다. 판매자 정보는 조건을 바꿀 수 없다.
- 재고는 "trusted catalog evidence → (b)" 점선으로 따로 그린다.

---

## 12. 구현 1단계: 권한 검증 먼저 (2026-11-26 밤, 연구자 결정)

**연구자 결정:** 권한 검증을 먼저 구현하고, 대화 맥락 검증(M1)은 나중에 붙인다.
- 1단계의 mandate(P, F_k)는 시나리오의 정답 사양으로 만든다.
- 2단계에서는 M1이 대화에서 P와 F_k를 만들고 근거(basis)를 검증한다.
- 그래서 "정답 mandate vs M1이 만든 mandate"를 비교하면 M1의 기여를 따로 잴 수 있다.

**구현한 파일** (표준 라이브러리만 사용, 모델·네트워크 호출 없음)

| 파일 | 내용 |
|---|---|
| `cdv/canon.py` | A-VIP와 같은 정규화 JSON, SHA-256. 서명은 HMAC-SHA256으로 흉내 낸다(공개키 서명이 아니라고 명시) |
| `cdv/mandate.py` | Line, Scope(브랜드·총액·필수 기능·수량·판매자·품목), Clause(subject, predicate, then, proof, scope_rule, ttl), Mandate 서명, VersionRegistry(최신 버전, 폐기) |
| `cdv/evidence.py` | AUTHORITY 표, `admissible`(Standing 규칙을 조항의 proof로 제한), Evidence, E1–E3, NonceStore, `clause_open`(scope_rule 포함) |
| `cdv/gate.py` | 검사 순서: mandate 서명 → V9 버전 → 세션 → A-VIP V1–V8(STRICT, A-LEX) → V12 결합 해시 → 장바구니 Capture 포함 → V10/V11 범위·조항. 판정은 ALLOW / CLARIFY / DENY와 사유 코드 |
| `adapters/avip.py` | A-VIP `mechanism` 패키지를 고치지 않고 불러온다. 위치는 submodule이 기본이고 `CDV_AVIP_BINDING`으로 바꿀 수 있다 |
| `tests/test_gate_scenarios.py` | 시나리오 1–13 + A-VIP 기록 검증, 17개 |

**시험 결과 (2026-11-26)**
- 17개 모두 통과했다. A-VIP는 고정 커밋 `0c1b538`의 복제본을 `CDV_AVIP_BINDING`으로 지정해 썼다.
- 검사 무력화 확인도 했다. 다음 검사를 일부러 끄면 해당 시험이 실패했다.
  - E2(`admissible`)를 항상 참으로 → 시험 03·09 실패
  - E1(서명)을 항상 참으로 → 04 실패
  - 버전 검사를 항상 참으로 → 08 실패
  - 결합 해시를 무시 → 11a 실패

**검토 반영 (연구자 쪽 AI 지적)**
- **M2b는 Standing의 "적용"이 아니라 "확장"이다.** AUTHORITY(criteria) = ∅은 새 술어 유형을 정의한다. 어려운 부분은 규칙이 아니라 "기준을 주장하는 문장"을 가려내는 추출이다. 그 정확도는 따로 잰다. 2단계 범위다.
- **AUTHORITY(stock)와 Standing의 s = u 충돌**
  - 조항의 `proof`로 고를 수 있게 했다.
    - `("platform",)`: Standing보다 좁다. 판매자 자신의 품절 주장으로는 조항이 열리지 않는다. 의도적으로 좁힌 것이고, 논문에 그렇게 명시한다.
    - `("platform", "seller_of_subject")`: Standing 규칙 그대로다. 같은 판매자의 "저가 품절, 고가 구매" 유도가 통과하는 한계가 있다(시험 09).
  - 실험의 기본값은 연구자가 정한다.
- **구성 요소 제거 실험(사전등록 초안에 추가할 것):** A-VIP만 / +E2 / +M2b / 전체의 네 조건에서 공격 성공률과 정당 실행률을 비교한다.
- **"A-VIP 구조 결속이 Selection 카트 68건 중 0건을 거부"는 원문에서 직접 확인하지 않았다.** 원문에 있는 것은 지출 규칙이 68/68을 드러냈다는 것(표 11)이다. 인용 전에 확인한다.

**아직 없는 것**
- CartTrace 어댑터(도구 결과 파싱, 품절 증거 원천, §9)
- 비교군
- M1, M2b
- 판매자 간 주장 귀속의 LLM 경로

---

## 13. 확정과 확인 결과 (2026-11-26 밤)

**품절 증거 출처 (연구자 확정)**
- 기본 정책은 `proof=("platform",)`(플랫폼만)이다.
- `("platform","seller_of_subject")`는 비교 실험 조건으로 유지한다.

**CartTrace의 품절 표현 (무과금 확인)**
- 품절은 판매자 글이 아니라 프로토콜의 구조화 필드로 나온다. 그래서 "플랫폼만" 조건에서도 실험이 성립한다. 모든 품절이 CLARIFY로 떨어지지 않는다.
  - 카탈로그 결과(`search_catalog`, `get_product`, `search_products`): `variants[].availability = {"available": false, "status": "out_of_stock"}`. 옵션 단위 `available: false`도 있다.
    - 확인한 표면: ucp_mcp, ucp_rest, webmcp, +mpp, ap2+ucp_rest, acp_rest+ucp_rest
  - 결제 단계 오류 코드: `send_payment_mandate`·`complete_checkout`의 `merchandise_out_of_stock`, `remove_cart_line`의 `out_of_stock`, `pay`의 "the reservation lapsed and the stock is gone"(verification-failed)
- 판매자 자유 글에도 재고 문장이 있다(예: "ALL ITEMS ARE AVAILABLE UNLESS MARKED AS SOLD OUT"). 이것은 판매자 발화로 처리한다.
- **가정(논문에 명시):** CartTrace에는 플랫폼과 상점이 따로 없다. 같은 상점이 구조화 API와 자유 글을 모두 낸다. "플랫폼 채널"은 구조화 필드를 뜻한다. 서명은 없다.

**작업 범위 (연구자 지시)**
- 어댑터 구현과 권한 검증 확장에는 더 시간을 쓰지 않는다.
- 다음 작업의 중심은 M1이다(`docs/M1_DESIGN.md`).
- 서명 주장의 경계는 `M1_DESIGN.md` §6을 따른다.
