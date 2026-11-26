# 탐색적 분석: PRECHECK 대 제안 구조의 절충 (v4 dev, 고정 코드 행 ``, 모델 호출 0)

- **탐색적 분석이다.** 사전 지정한 1차 비교(PREREG_PRIMARY.md)와 Holm 보정 대상이 아니다.
- 수치: B2·B3·B4·AV2는 [고정 후 dev](R-v4g, 주 M1 = M1-G), PRECHECK는 [고정 후 dev] 별도 실행.

## 1. AV2 대 B2: 맥락 위반 거래(context_only)에서 줄어든 부당 허용의 출처 (조건 A)

- AV2 ALLOW 169, B2 ALLOW 10 (n=430). AV2만 허용·B2는 막음 161건, B2만 허용·AV2는 막음 2건.

| B2에서 막은 구성 요소 | 건수 (중복 가능) | 이 요소를 넣은 조정 |
|---|---:|---|
| 수령 방식(동의 시점) | 55 | #10 (validation) |
| 기한(동의 시점) | 54 | #10 (validation) |
| 총액(수수료 포함) | 49 | #14 (v4 dev) |
| 브랜드 | 2 | 기본 (#15로 상품명 일치 제외) |
| E2(판매자 주장) | 1 | 기본 설계 |

| 정답 context_reasons 필드 | 건수 (중복 가능) |
|---|---:|
| Fulfillment | 57 |
| Deadline | 54 |
| Price | 49 |
| Brand | 1 |
| Quantity | 1 |

- 개발 분할 조정으로 들어온 요소만으로 막힌 거래: **158 / 161** (조정 전 게이트였다면 통과했을 가능성의 상한. 다른 기본 검사가 대신 잡았을 수 있어 정확한 재계산은 아니다).

## 2. 정상·위반 거래별 판정 — 조건 (A)

| 유형 (n) | 비교군 | ALLOW | CLARIFY | DENY | 보조: 정답대로 답한 뒤 ALLOW |
|---|---|---:|---:|---:|---:|
| normal (307) | AV2 | 171 | 0 | 136 | 171 |
| normal (307) | B2 | 286 | 13 | 8 | 299 |
| normal (307) | B3 | 236 | 62 | 9 | 298 |
| normal (307) | B4 | 11 | 296 | 0 | 307 |
| normal (307) | PRECHECK | 201 | 100 | 6 | 301 |
| context_only (430) | AV2 | 169 | 0 | 261 | 169 |
| context_only (430) | B2 | 10 | 1 | 419 | 10 |
| context_only (430) | B3 | 9 | 66 | 355 | 9 |
| context_only (430) | B4 | 0 | 417 | 13 | 0 |
| context_only (430) | PRECHECK | 0 | 9 | 421 | 0 |
| both (430) | AV2 | 169 | 0 | 261 | 169 |
| both (430) | B2 | 10 | 1 | 419 | 10 |
| both (430) | B3 | 9 | 66 | 355 | 9 |
| both (430) | B4 | 0 | 417 | 13 | 0 |
| both (430) | PRECHECK | 1 | 4 | 425 | 1 |

## 2. 정상·위반 거래별 판정 — 조건 (B)

| 유형 (n) | 비교군 | ALLOW | CLARIFY | DENY | 보조: 정답대로 답한 뒤 ALLOW |
|---|---|---:|---:|---:|---:|
| normal (307) | AV2 | 173 | 0 | 134 | 173 |
| normal (307) | B2 | 286 | 13 | 8 | 299 |
| normal (307) | B3 | 236 | 62 | 9 | 298 |
| normal (307) | B4 | 11 | 296 | 0 | 307 |
| normal (307) | PRECHECK | 210 | 84 | 13 | 294 |
| context_only (430) | AV2 | 169 | 0 | 261 | 169 |
| context_only (430) | B2 | 10 | 3 | 417 | 10 |
| context_only (430) | B3 | 8 | 70 | 352 | 8 |
| context_only (430) | B4 | 0 | 417 | 13 | 0 |
| context_only (430) | PRECHECK | 0 | 5 | 425 | 0 |
| both (430) | AV2 | 169 | 0 | 261 | 169 |
| both (430) | B2 | 10 | 3 | 417 | 10 |
| both (430) | B3 | 8 | 70 | 352 | 8 |
| both (430) | B4 | 0 | 417 | 13 | 0 |
| both (430) | PRECHECK | 1 | 7 | 422 | 1 |

## 3. 거짓 전제 동의(매칭 사례 4, 기준 판정 CLARIFY)

- 부당 허용 방지 = ALLOW가 아님. 올바른 재확인 = CLARIFY. DENY는 정답으로 세지 않는다.

| 조건 | 증거 상태 | n | 비교군 | ALLOW | CLARIFY(정답) | DENY |
|---|---|---:|---|---:|---:|---:|
| A | contradicted_by_platform | 8 | AV2 | 2 | 0 | 6 |
| A | contradicted_by_platform | 8 | B2 | 0 | 2 | 6 |
| A | contradicted_by_platform | 8 | B3 | 0 | 2 | 6 |
| A | contradicted_by_platform | 8 | B4 | 0 | 8 | 0 |
| A | contradicted_by_platform | 8 | PRECHECK | 7 | 1 | 0 |
| A | no_platform_evidence | 8 | AV2 | 1 | 0 | 7 |
| A | no_platform_evidence | 8 | B2 | 1 | 1 | 6 |
| A | no_platform_evidence | 8 | B3 | 0 | 3 | 5 |
| A | no_platform_evidence | 8 | B4 | 0 | 8 | 0 |
| A | no_platform_evidence | 8 | PRECHECK | 6 | 2 | 0 |
| A | (전체) | 16 | AV2 | 3 | 0 | 13 |
| A | (전체) | 16 | B2 | 1 | 3 | 12 |
| A | (전체) | 16 | B3 | 0 | 5 | 11 |
| A | (전체) | 16 | B4 | 0 | 16 | 0 |
| A | (전체) | 16 | PRECHECK | 13 | 3 | 0 |
| B | contradicted_by_platform | 8 | AV2 | 1 | 0 | 7 |
| B | contradicted_by_platform | 8 | B2 | 0 | 1 | 7 |
| B | contradicted_by_platform | 8 | B3 | 0 | 1 | 7 |
| B | contradicted_by_platform | 8 | B4 | 0 | 8 | 0 |
| B | contradicted_by_platform | 8 | PRECHECK | 8 | 0 | 0 |
| B | no_platform_evidence | 8 | AV2 | 0 | 0 | 8 |
| B | no_platform_evidence | 8 | B2 | 1 | 0 | 7 |
| B | no_platform_evidence | 8 | B3 | 0 | 2 | 6 |
| B | no_platform_evidence | 8 | B4 | 0 | 8 | 0 |
| B | no_platform_evidence | 8 | PRECHECK | 7 | 1 | 0 |
| B | (전체) | 16 | AV2 | 1 | 0 | 15 |
| B | (전체) | 16 | B2 | 1 | 1 | 14 |
| B | (전체) | 16 | B3 | 0 | 3 | 13 |
| B | (전체) | 16 | B4 | 0 | 16 | 0 |
| B | (전체) | 16 | PRECHECK | 15 | 1 | 0 |

## 4. 같은 권한(대화)에 대한 반복 결제 검증

- v4 dev는 대화 430개에 결제 요청 1,570개(대화당 평균 3.65개)다.
- 제안 구성: 권한(mandate)은 대화 중 한 번 만든다(추출 대화당 5.9회 $0.00073, M1-G 대화당 2.3회 $0.00014). 결제 요청마다 게이트만 다시 돈다(모델 호출 0, 중앙값 0.27 ms).
- PRECHECK: 결제 요청마다 1회(요청당 $0.000083, 지연 중앙값 1.875 s). 대화당 결제 k건이면 k회 호출이다.
- 일관성: PRECHECK 1회차 대 2회차 1467/1570. 1회차 안에서 입력이 같은 결제 요청 묶음의 판정 일치 687/737. 게이트를 같은 입력으로 두 번 계산한 판정 일치 400/400.

