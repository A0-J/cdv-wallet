# 통합 파이프라인 무과금 기능 시험 (4단계, validation, 2026-11-26)

- 스크립트: `eval/integrated/functional_validation.py`. 모델 호출 0. test 데이터 사용 없음.
- 파이프라인: 대화(t 이전) → FnCTOD 상태(저장된 것) → M1 v2 → 검증된 C/S → `ledger_to_mandate` → ECDSA 서명 → M2 게이트(`cdv/gate.py::authorize` + E2) → `cdv/verdict.py::integrated`.
- **이것은 성능 평가가 아니다.** (a)는 n=10 연결 확인이고, (b)는 정답 조건을 입력으로 쓴 참고 실험이다.

## (a) 파일럿 10여정 (실제 FnCTOD 출력, PLAN_v3 파일럿 2)

| 비교군 | ALLOW | CLARIFY | DENY |
|---|---:|---:|---:|
| B0 제안 검증 없음 | 10 | 0 | 0 |
| B1 M1 Only | 6 | 4 | 0 |
| B2 M2 Only | 10 | 0 | 0 |
| B3 M1+M2 | 10 | 0 | 0 |
| B4 M1+M2, 선택적 재확인 끔 | 6 | 4 | 0 |
| U 참고(정답 조건 mandate) | 10 | 0 | 0 |

- 10여정 중 8여정은 정상(RIGHT/RIGHT_BY_LUCK), 2여정은 WRONG이다. WRONG 2여정은 정답 조건 mandate(U)로도 통과한다. 결제 시점에 검사할 수 있는 조건(예산·수량·브랜드·묶음 수)을 어긴 것이 아니다.
- B1·B4의 확인 요청 4건의 원인: 연결하지 못한 참조(후보 여럿인 지시어, 목록 항목이 카탈로그와 연결 안 됨), 값 근거가 없는 수량. B3에서는 이 항목들을 받아들일 때와 아닐 때 게이트 판정이 같아서 묻지 않았다.
- **첫 실행에서 찾은 결함(고침):** 묶음 구매에서 한 상품을 고르면 S가 '장바구니 ⊆ S'로 작동해, 함께 사야 하는 나머지 상품까지 범위 밖으로 막았다(ep-535246e7fd35 RIGHT_BY_LUCK → DENY, ep-0ab7d93c2cef RIGHT → CLARIFY). 묶음 구매에서는 S를 '고른 상품이 장바구니에 반드시 포함됨'(`must_include`)으로 바꿨다. 첫 실행 결과는 `*_run1_before_bundle_fix.*`로 남겼다. 단위 시험 `test_pick_in_bundle_does_not_exclude_other_members`를 더했다.

## (b) 정답 조건 mandate 참고 실험 (validation 장바구니 있는 3,657여정 전체)

- 입력 검사로 멈춘 여정: 0. 캡처에 없는 장바구니 상품(NOT_CAPTURED): 0. A-VIP 실패: 1(WRONG 1여정).
- 정답 조건(숨은 사양의 예산·수량·브랜드·묶음 수)으로 Mandate를 만들고 같은 게이트에 넣었을 때:

| CartTrace 결과 | 수 | ALLOW | CLARIFY | DENY | 결제 시점에 막힌 비율 |
|---|---:|---:|---:|---:|---:|
| RIGHT | 2,596 | 2,593 | 3 | 0 | 0.1% |
| RIGHT_BY_LUCK | 143 | 143 | 0 | 0 | 0% |
| WRONG | 730 | 631 | 6 | 93 | 13.6% |
| WRONG_HIDDEN | 188 | 177 | 0 | 11 | 5.9% |

- **CartTrace의 WRONG은 대부분 결제 권한 위반과 같은 뜻이 아니다.** 정답 조건을 정확히 알아도 WRONG 장바구니의 86%는 결제 시점 검사(예산·수량·브랜드·묶음 수)로 막을 수 없다. 남은 위반은 상품 종류·속성(색·사이즈)·대체 선호·최저가 등이다(진단 D3: validation 위반 918건 중 317건은 장바구니 상품이 허용 상품 밖). 이 중 상품 종류와 사용자가 고른 상품(S)은 M1 v2가 Mandate에 넣지만, 속성·선호·최저가는 아직 Mandate 항목이 아니다.
- 따라서 통합 평가의 '위반 거래'는 WRONG 표지가 아니라 사용자 발화 기준표(`docs/INTEGRATED_EVAL_DESIGN.md` 10.2)로 정해야 한다. WRONG 중 결제 권한과 관련 없는 실패는 별도 유형으로 보고한다.
- 정상 RIGHT의 확인 요청 3건은 모두 E2(고른 상품의 설명에 다른 상품의 재고 문장)다. 정상 데이터에서 E2의 오경보율은 3/2,596이다.
