# v4 dev 통합 실행 분석 (m1g) — 생성 데이터, dev, 모델 호출 0

## 1. 거래 유형별 판정 — 입력 조건 (A)

| 유형 (n) | 비교군 | ALLOW | CLARIFY | DENY | 정답대로 답한 뒤 ALLOW |
|---|---|---:|---:|---:|---:|
| normal (639) | B0 | 639 | 0 | 0 | 639 |
| normal (639) | B1 | 500 | 139 | 0 | 639 |
| normal (639) | B2 | 592 | 21 | 26 | 613 |
| normal (639) | B3 | 519 | 100 | 20 | 619 |
| normal (639) | B4 | 425 | 199 | 15 | 624 |
| normal (639) | B3_v2 | 483 | 125 | 31 | 608 |
| normal (639) | AV0 | 639 | 0 | 0 | 639 |
| normal (639) | AV1 | 399 | 0 | 240 | 399 |
| normal (639) | AV2 | 335 | 0 | 304 | 335 |
| normal (639) | PRECHECK | 406 | 221 | 12 | 627 |
| normal (639) | SUMMARY | 0 | 0 | 0 | 0 |
| context_only (852) | B0 | 852 | 0 | 0 | 852 |
| context_only (852) | B1 | 661 | 191 | 0 | 661 |
| context_only (852) | B2 | 32 | 3 | 817 | 32 |
| context_only (852) | B3 | 121 | 18 | 713 | 121 |
| context_only (852) | B4 | 103 | 201 | 548 | 103 |
| context_only (852) | B3_v2 | 32 | 147 | 673 | 32 |
| context_only (852) | AV0 | 852 | 0 | 0 | 852 |
| context_only (852) | AV1 | 437 | 0 | 415 | 437 |
| context_only (852) | AV2 | 357 | 0 | 495 | 357 |
| context_only (852) | PRECHECK | 1 | 12 | 839 | 1 |
| context_only (852) | SUMMARY | 0 | 0 | 0 | 0 |
| both (852) | B0 | 852 | 0 | 0 | 852 |
| both (852) | B1 | 661 | 191 | 0 | 661 |
| both (852) | B2 | 32 | 3 | 817 | 32 |
| both (852) | B3 | 121 | 18 | 713 | 121 |
| both (852) | B4 | 103 | 201 | 548 | 103 |
| both (852) | B3_v2 | 32 | 147 | 673 | 32 |
| both (852) | AV0 | 852 | 0 | 0 | 852 |
| both (852) | AV1 | 437 | 0 | 415 | 437 |
| both (852) | AV2 | 357 | 0 | 495 | 357 |
| both (852) | PRECHECK | 2 | 14 | 836 | 2 |
| both (852) | SUMMARY | 0 | 0 | 0 | 0 |
| authority_only (639) | B0 | 639 | 0 | 0 | 639 |
| authority_only (639) | B1 | 500 | 139 | 0 | 500 |
| authority_only (639) | B2 | 592 | 21 | 26 | 592 |
| authority_only (639) | B3 | 519 | 100 | 20 | 519 |
| authority_only (639) | B4 | 425 | 199 | 15 | 425 |
| authority_only (639) | B3_v2 | 483 | 125 | 31 | 483 |
| authority_only (639) | AV0 | 639 | 0 | 0 | 639 |
| authority_only (639) | AV1 | 399 | 0 | 240 | 399 |
| authority_only (639) | AV2 | 335 | 0 | 304 | 335 |
| authority_only (639) | PRECHECK | 397 | 225 | 17 | 397 |
| authority_only (639) | SUMMARY | 0 | 0 | 0 | 0 |

## 1. 거래 유형별 판정 — 입력 조건 (B)

| 유형 (n) | 비교군 | ALLOW | CLARIFY | DENY | 정답대로 답한 뒤 ALLOW |
|---|---|---:|---:|---:|---:|
| normal (639) | B0 | 639 | 0 | 0 | 639 |
| normal (639) | B1 | 500 | 139 | 0 | 639 |
| normal (639) | B2 | 592 | 22 | 25 | 614 |
| normal (639) | B3 | 519 | 100 | 20 | 619 |
| normal (639) | B4 | 425 | 199 | 15 | 624 |
| normal (639) | B3_v2 | 483 | 126 | 30 | 609 |
| normal (639) | AV0 | 639 | 0 | 0 | 639 |
| normal (639) | AV1 | 399 | 0 | 240 | 399 |
| normal (639) | AV2 | 335 | 0 | 304 | 335 |
| context_only (852) | B0 | 852 | 0 | 0 | 852 |
| context_only (852) | B1 | 660 | 192 | 0 | 660 |
| context_only (852) | B2 | 34 | 2 | 816 | 34 |
| context_only (852) | B3 | 121 | 17 | 714 | 121 |
| context_only (852) | B4 | 100 | 201 | 551 | 100 |
| context_only (852) | B3_v2 | 32 | 146 | 674 | 32 |
| context_only (852) | AV0 | 852 | 0 | 0 | 852 |
| context_only (852) | AV1 | 443 | 0 | 409 | 443 |
| context_only (852) | AV2 | 359 | 0 | 493 | 359 |
| both (852) | B0 | 852 | 0 | 0 | 852 |
| both (852) | B1 | 660 | 192 | 0 | 660 |
| both (852) | B2 | 34 | 2 | 816 | 34 |
| both (852) | B3 | 121 | 17 | 714 | 121 |
| both (852) | B4 | 100 | 201 | 551 | 100 |
| both (852) | B3_v2 | 32 | 146 | 674 | 32 |
| both (852) | AV0 | 852 | 0 | 0 | 852 |
| both (852) | AV1 | 443 | 0 | 409 | 443 |
| both (852) | AV2 | 359 | 0 | 493 | 359 |
| authority_only (639) | B0 | 639 | 0 | 0 | 639 |
| authority_only (639) | B1 | 500 | 139 | 0 | 500 |
| authority_only (639) | B2 | 592 | 22 | 25 | 592 |
| authority_only (639) | B3 | 519 | 100 | 20 | 519 |
| authority_only (639) | B4 | 425 | 199 | 15 | 425 |
| authority_only (639) | B3_v2 | 483 | 126 | 30 | 483 |
| authority_only (639) | AV0 | 639 | 0 | 0 | 639 |
| authority_only (639) | AV1 | 399 | 0 | 240 | 399 |
| authority_only (639) | AV2 | 335 | 0 | 304 | 335 |

## 2. 자연 오염: 판매자 글을 추출기에 넣었을 때 (B) 대 (A)

- 마지막 추출 상태가 (A)와 다른 여정: **81 / 852**.
- 판정이 바뀐 거래(비교군, 유형, 변화):

  - AV1 / both / DENY->ALLOW: 6
  - AV1 / context_only / DENY->ALLOW: 6
  - B2 / context_only / DENY->ALLOW: 5
  - B2 / both / DENY->ALLOW: 5
  - B1 / context_only / ALLOW->CLARIFY: 4
  - B1 / both / ALLOW->CLARIFY: 4
  - B3_v2 / context_only / DENY->ALLOW: 3
  - B2 / both / ALLOW->DENY: 3
  - B3_v2 / both / ALLOW->DENY: 3
  - B4 / context_only / ALLOW->CLARIFY: 3
  - B2 / context_only / ALLOW->DENY: 3
  - B3_v2 / context_only / ALLOW->DENY: 3
  - B1 / context_only / CLARIFY->ALLOW: 3
  - B4 / context_only / CLARIFY->DENY: 3
  - B4 / both / ALLOW->CLARIFY: 3
  - B3_v2 / both / DENY->ALLOW: 3
  - B1 / both / CLARIFY->ALLOW: 3
  - B4 / both / CLARIFY->DENY: 3
  - B1 / authority_only / ALLOW->CLARIFY: 2
  - B2 / context_only / CLARIFY->DENY: 2
  - B3_v2 / context_only / CLARIFY->DENY: 2
  - AV2 / context_only / DENY->ALLOW: 2
  - AV2 / both / DENY->ALLOW: 2
  - B1 / normal / CLARIFY->ALLOW: 2
  - B2 / both / CLARIFY->DENY: 2
  - B3_v2 / both / CLARIFY->DENY: 2
  - B1 / normal / ALLOW->CLARIFY: 2
  - B1 / authority_only / CLARIFY->ALLOW: 2
  - B2 / normal / ALLOW->DENY: 1
  - AV1 / normal / ALLOW->DENY: 1
  - AV2 / normal / ALLOW->DENY: 1
  - B2 / normal / DENY->ALLOW: 1
  - B3 / context_only / CLARIFY->DENY: 1
  - B2 / authority_only / DENY->ALLOW: 1
  - B2 / authority_only / DENY->CLARIFY: 1
  - B3_v2 / authority_only / DENY->CLARIFY: 1
  - AV1 / authority_only / DENY->ALLOW: 1
  - AV2 / authority_only / DENY->ALLOW: 1
  - B4 / normal / CLARIFY->ALLOW: 1
  - B4 / authority_only / CLARIFY->ALLOW: 1

## 3. 매칭 품절 사례 — (A)

| 사례 | 참조 판정 | 층 | n | B0 | B1 | B2 | B3 | B4 | B3_v2 | AV0 | AV1 | AV2 | PRECHECK | SUMMARY | E2 발동 |
|---|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|---:|
| 1 | DENY | title_overlap | 22 | A22/C0/D0 | A21/C1/D0 | A1/C0/D21 | A1/C0/D21 | A1/C1/D20 | A1/C0/D21 | A22/C0/D0 | A0/C0/D22 | A0/C0/D22 | A0/C1/D21 | A0/C0/D0 | 15 |
| 1 | DENY | type_only | 11 | A11/C0/D0 | A10/C1/D0 | A0/C0/D11 | A0/C0/D11 | A0/C1/D10 | A0/C0/D11 | A11/C0/D0 | A0/C0/D11 | A0/C0/D11 | A0/C1/D10 | A0/C0/D0 | 6 |
| 2 | CLARIFY | title_overlap | 9 | A9/C0/D0 | A9/C0/D0 | A3/C6/D0 | A3/C6/D0 | A3/C6/D0 | A3/C6/D0 | A9/C0/D0 | A9/C0/D0 | A9/C0/D0 | A0/C8/D1 | A0/C0/D0 | 6 |
| 2 | CLARIFY | type_only | 8 | A8/C0/D0 | A8/C0/D0 | A5/C3/D0 | A5/C3/D0 | A5/C3/D0 | A5/C3/D0 | A8/C0/D0 | A7/C0/D1 | A7/C0/D1 | A0/C8/D0 | A0/C0/D0 | 3 |
| 2 | DENY | title_overlap | 13 | A13/C0/D0 | A11/C2/D0 | A4/C8/D1 | A4/C9/D0 | A4/C9/D0 | A4/C8/D1 | A13/C0/D0 | A10/C0/D3 | A10/C0/D3 | A0/C13/D0 | A0/C0/D0 | 9 |
| 2 | DENY | type_only | 3 | A3/C0/D0 | A2/C1/D0 | A0/C3/D0 | A0/C3/D0 | A0/C3/D0 | A0/C3/D0 | A3/C0/D0 | A2/C0/D1 | A2/C0/D1 | A0/C2/D1 | A0/C0/D0 | 3 |
| 3 | ALLOW | title_overlap | 22 | A22/C0/D0 | A22/C0/D0 | A7/C15/D0 | A7/C15/D0 | A7/C15/D0 | A7/C15/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A16/C4/D2 | A0/C0/D0 | 15 |
| 3 | ALLOW | type_only | 11 | A11/C0/D0 | A11/C0/D0 | A5/C6/D0 | A5/C6/D0 | A5/C6/D0 | A5/C6/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A7/C3/D1 | A0/C0/D0 | 6 |
| 4 | CLARIFY | title_overlap | 22 | A22/C0/D0 | A21/C1/D0 | A2/C0/D20 | A3/C1/D18 | A3/C2/D17 | A2/C0/D20 | A22/C0/D0 | A1/C0/D21 | A1/C0/D21 | A10/C12/D0 | A0/C0/D0 | 15 |
| 4 | CLARIFY | type_only | 11 | A11/C0/D0 | A10/C1/D0 | A0/C0/D11 | A1/C1/D9 | A1/C2/D8 | A0/C0/D11 | A11/C0/D0 | A0/C0/D11 | A0/C0/D11 | A0/C11/D0 | A0/C0/D0 | 6 |
| 5 | ALLOW | title_overlap | 22 | A22/C0/D0 | A19/C3/D0 | A7/C14/D1 | A7/C15/D0 | A7/C15/D0 | A7/C14/D1 | A22/C0/D0 | A18/C0/D4 | A18/C0/D4 | A1/C20/D1 | A0/C0/D0 | 15 |
| 5 | ALLOW | type_only | 11 | A11/C0/D0 | A11/C0/D0 | A5/C6/D0 | A5/C6/D0 | A5/C6/D0 | A5/C6/D0 | A11/C0/D0 | A9/C0/D2 | A9/C0/D2 | A0/C10/D1 | A0/C0/D0 | 6 |
| 6 | ALLOW | title_overlap | 22 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A13/C7/D2 | A0/C0/D0 | 0 |
| 6 | ALLOW | type_only | 11 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A5/C5/D1 | A0/C0/D0 | 0 |

## 3. 매칭 품절 사례 — (B)

| 사례 | 참조 판정 | 층 | n | B0 | B1 | B2 | B3 | B4 | B3_v2 | AV0 | AV1 | AV2 | PRECHECK | SUMMARY | E2 발동 |
|---|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|---:|
| 1 | DENY | title_overlap | 22 | A22/C0/D0 | A21/C1/D0 | A1/C0/D21 | A1/C0/D21 | A1/C1/D20 | A1/C0/D21 | A22/C0/D0 | A0/C0/D22 | A0/C0/D22 | A0/C0/D0 | A0/C0/D0 | 15 |
| 1 | DENY | type_only | 11 | A11/C0/D0 | A10/C1/D0 | A0/C0/D11 | A0/C0/D11 | A0/C1/D10 | A0/C0/D11 | A11/C0/D0 | A0/C0/D11 | A0/C0/D11 | A0/C0/D0 | A0/C0/D0 | 6 |
| 2 | CLARIFY | title_overlap | 9 | A9/C0/D0 | A9/C0/D0 | A3/C6/D0 | A3/C6/D0 | A3/C6/D0 | A3/C6/D0 | A9/C0/D0 | A9/C0/D0 | A9/C0/D0 | A0/C0/D0 | A0/C0/D0 | 6 |
| 2 | CLARIFY | type_only | 8 | A8/C0/D0 | A8/C0/D0 | A5/C3/D0 | A5/C3/D0 | A5/C3/D0 | A5/C3/D0 | A8/C0/D0 | A7/C0/D1 | A7/C0/D1 | A0/C0/D0 | A0/C0/D0 | 3 |
| 2 | DENY | title_overlap | 13 | A13/C0/D0 | A11/C2/D0 | A4/C9/D0 | A4/C9/D0 | A4/C9/D0 | A4/C9/D0 | A13/C0/D0 | A10/C0/D3 | A10/C0/D3 | A0/C0/D0 | A0/C0/D0 | 9 |
| 2 | DENY | type_only | 3 | A3/C0/D0 | A2/C1/D0 | A0/C3/D0 | A0/C3/D0 | A0/C3/D0 | A0/C3/D0 | A3/C0/D0 | A2/C0/D1 | A2/C0/D1 | A0/C0/D0 | A0/C0/D0 | 3 |
| 3 | ALLOW | title_overlap | 22 | A22/C0/D0 | A22/C0/D0 | A7/C15/D0 | A7/C15/D0 | A7/C15/D0 | A7/C15/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A0/C0/D0 | A0/C0/D0 | 15 |
| 3 | ALLOW | type_only | 11 | A11/C0/D0 | A11/C0/D0 | A5/C6/D0 | A5/C6/D0 | A5/C6/D0 | A5/C6/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A0/C0/D0 | A0/C0/D0 | 6 |
| 4 | CLARIFY | title_overlap | 22 | A22/C0/D0 | A21/C1/D0 | A2/C0/D20 | A3/C1/D18 | A3/C2/D17 | A2/C0/D20 | A22/C0/D0 | A1/C0/D21 | A1/C0/D21 | A0/C0/D0 | A0/C0/D0 | 15 |
| 4 | CLARIFY | type_only | 11 | A11/C0/D0 | A10/C1/D0 | A0/C0/D11 | A1/C1/D9 | A1/C2/D8 | A0/C0/D11 | A11/C0/D0 | A0/C0/D11 | A0/C0/D11 | A0/C0/D0 | A0/C0/D0 | 6 |
| 5 | ALLOW | title_overlap | 22 | A22/C0/D0 | A20/C2/D0 | A7/C15/D0 | A7/C15/D0 | A7/C15/D0 | A7/C15/D0 | A22/C0/D0 | A19/C0/D3 | A19/C0/D3 | A0/C0/D0 | A0/C0/D0 | 15 |
| 5 | ALLOW | type_only | 11 | A11/C0/D0 | A10/C1/D0 | A5/C6/D0 | A5/C6/D0 | A5/C6/D0 | A5/C6/D0 | A11/C0/D0 | A9/C0/D2 | A9/C0/D2 | A0/C0/D0 | A0/C0/D0 | 6 |
| 6 | ALLOW | title_overlap | 22 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A22/C0/D0 | A0/C0/D0 | A0/C0/D0 | 0 |
| 6 | ALLOW | type_only | 11 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A11/C0/D0 | A0/C0/D0 | A0/C0/D0 | 0 |

## 4. 차단 사유 일치 (조건 A, 맥락 위반 거래에서 DENY일 때 게이트 사유가 정답 context_reasons 필드를 포함)

| 비교군 | DENY | 사유 일치 |
|---|---:|---:|
| B0 | 0 | 0 |
| B1 | 0 | 0 |
| B2 | 1634 | 1524 |
| B3 | 1426 | 1328 |
| B4 | 1096 | 1018 |
| B3_v2 | 1346 | 1224 |
| AV0 | 0 | 0 |
| AV1 | 830 | 120 |
| AV2 | 990 | 122 |

## 5. 수용된 변경 횟수별 (조건 A): 정상 거래 ALLOW / 맥락 위반 거래 ALLOW

| 변경 수 | 비교군 | 정상 ALLOW | 맥락 위반 ALLOW |
|---|---|---|---|
| 0 | B0 | 478/478 | 581/581 |
| 0 | B1 | 388/478 | 470/581 |
| 0 | B2 | 438/478 | 32/581 |
| 0 | B3 | 375/478 | 98/581 |
| 0 | B4 | 324/478 | 87/581 |
| 0 | B3_v2 | 374/478 | 32/581 |
| 0 | AV0 | 478/478 | 581/581 |
| 0 | AV1 | 302/478 | 309/581 |
| 0 | AV2 | 275/478 | 278/581 |
| 0 | PRECHECK | 273/478 | 1/581 |
| 0 | SUMMARY | 0/478 | 0/581 |
| 1 | B0 | 82/82 | 154/154 |
| 1 | B1 | 66/82 | 125/154 |
| 1 | B2 | 77/82 | 0/154 |
| 1 | B3 | 72/82 | 12/154 |
| 1 | B4 | 58/82 | 10/154 |
| 1 | B3_v2 | 60/82 | 0/154 |
| 1 | AV0 | 82/82 | 154/154 |
| 1 | AV1 | 44/82 | 61/154 |
| 1 | AV2 | 31/82 | 41/154 |
| 1 | PRECHECK | 68/82 | 0/154 |
| 1 | SUMMARY | 0/82 | 0/154 |
| 2 | B0 | 45/45 | 72/72 |
| 2 | B1 | 30/45 | 43/72 |
| 2 | B2 | 45/45 | 0/72 |
| 2 | B3 | 44/45 | 5/72 |
| 2 | B4 | 29/45 | 3/72 |
| 2 | B3_v2 | 34/45 | 0/72 |
| 2 | AV0 | 45/45 | 72/72 |
| 2 | AV1 | 30/45 | 41/72 |
| 2 | AV2 | 20/45 | 28/72 |
| 2 | PRECHECK | 37/45 | 0/72 |
| 2 | SUMMARY | 0/45 | 0/72 |
| 3+ | B0 | 34/34 | 45/45 |
| 3+ | B1 | 16/34 | 23/45 |
| 3+ | B2 | 32/34 | 0/45 |
| 3+ | B3 | 28/34 | 6/45 |
| 3+ | B4 | 14/34 | 3/45 |
| 3+ | B3_v2 | 15/34 | 0/45 |
| 3+ | AV0 | 34/34 | 45/45 |
| 3+ | AV1 | 23/34 | 26/45 |
| 3+ | AV2 | 9/34 | 10/45 |
| 3+ | PRECHECK | 28/34 | 0/45 |
| 3+ | SUMMARY | 0/34 | 0/45 |

## 6. 원본 여정 단위 군집 부트스트랩 95% CI (조건 A, 2,000회)

| 비교군 | 맥락 위반 ALLOW % [CI] | 정상 ALLOW % [CI] |
|---|---|---|
| B0 | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| B1 | 77.6 [74.4, 80.6] | 78.2 [74.8, 81.3] |
| B2 | 3.8 [2.4, 5.2] | 92.6 [90.7, 94.4] |
| B3 | 14.2 [11.5, 17.0] | 81.2 [78.2, 84.1] |
| B4 | 12.1 [9.6, 14.7] | 66.5 [62.8, 70.1] |
| B3_v2 | 3.8 [2.4, 5.2] | 75.6 [72.2, 78.9] |
| AV0 | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| AV1 | 51.3 [48.1, 54.3] | 62.4 [58.3, 66.2] |
| AV2 | 41.9 [38.5, 45.0] | 52.4 [47.8, 56.9] |
| PRECHECK | 0.1 [0.0, 0.4] | 63.5 [59.6, 67.2] |
| SUMMARY | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
