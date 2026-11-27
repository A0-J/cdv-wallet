# 탐색적 분석: PRECHECK 대 제안 구조의 절충 (v4 dev, 고정 코드 행 `m1g`, 모델 호출 0)

- **탐색적 분석이다.** 사전 지정한 1차 비교(PREREG_PRIMARY.md)와 Holm 보정 대상이 아니다.
- 수치: B2·B3·B4·AV2는 [고정 후 dev](R-v4g, 주 M1 = M1-G), PRECHECK는 [고정 후 dev] 별도 실행.

## 1. AV2 대 B2: 맥락 위반 거래(context_only)에서 줄어든 부당 허용의 출처 (조건 A)

- AV2 ALLOW 357, B2 ALLOW 32 (n=852). AV2만 허용·B2는 막음 330건, B2만 허용·AV2는 막음 5건.

| B2에서 막은 구성 요소 | 건수 (중복 가능) | 이 요소를 넣은 조정 |
|---|---:|---|
| 총액(수수료 포함) | 113 | #14 (v4 dev) |
| 수령 방식(동의 시점) | 110 | #10 (validation) |
| 기한(동의 시점) | 104 | #10 (validation) |
| E2(판매자 주장) | 3 | 기본 설계 |

| 정답 context_reasons 필드 | 건수 (중복 가능) |
|---|---:|
| Price | 114 |
| Fulfillment | 112 |
| Deadline | 104 |

- 개발 분할 조정으로 들어온 요소만으로 막힌 거래: **327 / 330** (조정 전 게이트였다면 통과했을 가능성의 상한. 다른 기본 검사가 대신 잡았을 수 있어 정확한 재계산은 아니다).

## 2. 정상·위반 거래별 판정 — 조건 (A)

| 유형 (n) | 비교군 | ALLOW | CLARIFY | DENY | 보조: 정답대로 답한 뒤 ALLOW |
|---|---|---:|---:|---:|---:|
| normal (639) | AV2 | 335 | 0 | 304 | 335 |
| normal (639) | B2 | 592 | 21 | 26 | 613 |
| normal (639) | B3 | 519 | 100 | 20 | 619 |
| normal (639) | B4 | 425 | 199 | 15 | 624 |
| normal (639) | PRECHECK | 406 | 221 | 12 | 627 |
| context_only (852) | AV2 | 357 | 0 | 495 | 357 |
| context_only (852) | B2 | 32 | 3 | 817 | 32 |
| context_only (852) | B3 | 121 | 18 | 713 | 121 |
| context_only (852) | B4 | 103 | 201 | 548 | 103 |
| context_only (852) | PRECHECK | 1 | 12 | 839 | 1 |
| both (852) | AV2 | 357 | 0 | 495 | 357 |
| both (852) | B2 | 32 | 3 | 817 | 32 |
| both (852) | B3 | 121 | 18 | 713 | 121 |
| both (852) | B4 | 103 | 201 | 548 | 103 |
| both (852) | PRECHECK | 2 | 14 | 836 | 2 |

## 2. 정상·위반 거래별 판정 — 조건 (B)

| 유형 (n) | 비교군 | ALLOW | CLARIFY | DENY | 보조: 정답대로 답한 뒤 ALLOW |
|---|---|---:|---:|---:|---:|
| normal (639) | AV2 | 335 | 0 | 304 | 335 |
| normal (639) | B2 | 592 | 22 | 25 | 614 |
| normal (639) | B3 | 519 | 100 | 20 | 619 |
| normal (639) | B4 | 425 | 199 | 15 | 624 |
| normal (639) | PRECHECK | 437 | 186 | 16 | 623 |
| context_only (852) | AV2 | 359 | 0 | 493 | 359 |
| context_only (852) | B2 | 34 | 2 | 816 | 34 |
| context_only (852) | B3 | 121 | 17 | 714 | 121 |
| context_only (852) | B4 | 100 | 201 | 551 | 100 |
| context_only (852) | PRECHECK | 9 | 14 | 829 | 9 |
| both (852) | AV2 | 359 | 0 | 493 | 359 |
| both (852) | B2 | 34 | 2 | 816 | 34 |
| both (852) | B3 | 121 | 17 | 714 | 121 |
| both (852) | B4 | 100 | 201 | 551 | 100 |
| both (852) | PRECHECK | 8 | 12 | 832 | 8 |

## 3. 거짓 전제 동의(매칭 사례 4, 기준 판정 CLARIFY)

- 부당 허용 방지 = ALLOW가 아님. 올바른 재확인 = CLARIFY. DENY는 정답으로 세지 않는다.

| 조건 | 증거 상태 | n | 비교군 | ALLOW | CLARIFY(정답) | DENY |
|---|---|---:|---|---:|---:|---:|
| A | contradicted_by_platform | 16 | AV2 | 0 | 0 | 16 |
| A | contradicted_by_platform | 16 | B2 | 0 | 0 | 16 |
| A | contradicted_by_platform | 16 | B3 | 1 | 1 | 14 |
| A | contradicted_by_platform | 16 | B4 | 1 | 2 | 13 |
| A | contradicted_by_platform | 16 | PRECHECK | 5 | 11 | 0 |
| A | no_platform_evidence | 17 | AV2 | 1 | 0 | 16 |
| A | no_platform_evidence | 17 | B2 | 2 | 0 | 15 |
| A | no_platform_evidence | 17 | B3 | 3 | 1 | 13 |
| A | no_platform_evidence | 17 | B4 | 3 | 2 | 12 |
| A | no_platform_evidence | 17 | PRECHECK | 5 | 12 | 0 |
| A | (전체) | 33 | AV2 | 1 | 0 | 32 |
| A | (전체) | 33 | B2 | 2 | 0 | 31 |
| A | (전체) | 33 | B3 | 4 | 2 | 27 |
| A | (전체) | 33 | B4 | 4 | 4 | 25 |
| A | (전체) | 33 | PRECHECK | 10 | 23 | 0 |
| B | contradicted_by_platform | 16 | AV2 | 0 | 0 | 16 |
| B | contradicted_by_platform | 16 | B2 | 0 | 0 | 16 |
| B | contradicted_by_platform | 16 | B3 | 1 | 1 | 14 |
| B | contradicted_by_platform | 16 | B4 | 1 | 2 | 13 |
| B | contradicted_by_platform | 16 | PRECHECK | 5 | 11 | 0 |
| B | no_platform_evidence | 17 | AV2 | 1 | 0 | 16 |
| B | no_platform_evidence | 17 | B2 | 2 | 0 | 15 |
| B | no_platform_evidence | 17 | B3 | 3 | 1 | 13 |
| B | no_platform_evidence | 17 | B4 | 3 | 2 | 12 |
| B | no_platform_evidence | 17 | PRECHECK | 4 | 13 | 0 |
| B | (전체) | 33 | AV2 | 1 | 0 | 32 |
| B | (전체) | 33 | B2 | 2 | 0 | 31 |
| B | (전체) | 33 | B3 | 4 | 2 | 27 |
| B | (전체) | 33 | B4 | 4 | 4 | 25 |
| B | (전체) | 33 | PRECHECK | 9 | 24 | 0 |

## 4. 같은 권한(대화)에 대한 반복 결제 검증

- v4 dev는 대화 430개에 결제 요청 1,570개(대화당 평균 3.65개)다.
- 제안 구성: 권한(mandate)은 대화 중 한 번 만든다(추출 대화당 5.9회 $0.00073, M1-G 대화당 2.3회 $0.00014). 결제 요청마다 게이트만 다시 돈다(모델 호출 0, 중앙값 0.27 ms).
- PRECHECK: 결제 요청마다 1회(요청당 $0.000083, 지연 중앙값 1.875 s). 대화당 결제 k건이면 k회 호출이다.
- 일관성: PRECHECK 1회차 대 2회차 1467/1570. 1회차 안에서 입력이 같은 결제 요청 묶음의 판정 일치 1369/1491. 게이트를 같은 입력으로 두 번 계산한 판정 일치 400/400.

