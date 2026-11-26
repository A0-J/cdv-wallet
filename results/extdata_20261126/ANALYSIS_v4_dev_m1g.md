# v4 dev 통합 실행 분석 (m1g) — 생성 데이터, dev, 모델 호출 0

## 1. 거래 유형별 판정 — 입력 조건 (A)

| 유형 (n) | 비교군 | ALLOW | CLARIFY | DENY | 정답대로 답한 뒤 ALLOW |
|---|---|---:|---:|---:|---:|
| normal (307) | B0 | 307 | 0 | 0 | 307 |
| normal (307) | B1 | 206 | 101 | 0 | 307 |
| normal (307) | B2 | 286 | 13 | 8 | 299 |
| normal (307) | B3 | 246 | 52 | 9 | 298 |
| normal (307) | B4 | 178 | 123 | 6 | 301 |
| normal (307) | B3_v2 | 236 | 62 | 9 | 298 |
| normal (307) | AV0 | 307 | 0 | 0 | 307 |
| normal (307) | AV1 | 205 | 0 | 102 | 205 |
| normal (307) | AV2 | 171 | 0 | 136 | 171 |
| normal (307) | PRECHECK | 201 | 100 | 6 | 301 |
| normal (307) | SUMMARY | 224 | 5 | 78 | 229 |
| context_only (430) | B0 | 430 | 0 | 0 | 430 |
| context_only (430) | B1 | 264 | 166 | 0 | 264 |
| context_only (430) | B2 | 9 | 4 | 417 | 9 |
| context_only (430) | B3 | 60 | 34 | 336 | 60 |
| context_only (430) | B4 | 49 | 173 | 208 | 49 |
| context_only (430) | B3_v2 | 8 | 69 | 353 | 8 |
| context_only (430) | AV0 | 430 | 0 | 0 | 430 |
| context_only (430) | AV1 | 217 | 0 | 213 | 217 |
| context_only (430) | AV2 | 169 | 0 | 261 | 169 |
| context_only (430) | PRECHECK | 0 | 9 | 421 | 0 |
| context_only (430) | SUMMARY | 25 | 1 | 404 | 25 |
| both (430) | B0 | 430 | 0 | 0 | 430 |
| both (430) | B1 | 267 | 163 | 0 | 267 |
| both (430) | B2 | 9 | 4 | 417 | 9 |
| both (430) | B3 | 63 | 32 | 335 | 63 |
| both (430) | B4 | 50 | 171 | 209 | 50 |
| both (430) | B3_v2 | 8 | 69 | 353 | 8 |
| both (430) | AV0 | 430 | 0 | 0 | 430 |
| both (430) | AV1 | 217 | 0 | 213 | 217 |
| both (430) | AV2 | 169 | 0 | 261 | 169 |
| both (430) | PRECHECK | 1 | 4 | 425 | 1 |
| both (430) | SUMMARY | 25 | 1 | 404 | 25 |
| authority_only (307) | B0 | 307 | 0 | 0 | 307 |
| authority_only (307) | B1 | 207 | 100 | 0 | 207 |
| authority_only (307) | B2 | 286 | 13 | 8 | 286 |
| authority_only (307) | B3 | 245 | 52 | 10 | 245 |
| authority_only (307) | B4 | 180 | 120 | 7 | 180 |
| authority_only (307) | B3_v2 | 236 | 62 | 9 | 236 |
| authority_only (307) | AV0 | 307 | 0 | 0 | 307 |
| authority_only (307) | AV1 | 205 | 0 | 102 | 205 |
| authority_only (307) | AV2 | 171 | 0 | 136 | 171 |
| authority_only (307) | PRECHECK | 197 | 103 | 7 | 197 |
| authority_only (307) | SUMMARY | 224 | 5 | 78 | 224 |

## 1. 거래 유형별 판정 — 입력 조건 (B)

| 유형 (n) | 비교군 | ALLOW | CLARIFY | DENY | 정답대로 답한 뒤 ALLOW |
|---|---|---:|---:|---:|---:|
| normal (307) | B0 | 307 | 0 | 0 | 307 |
| normal (307) | B1 | 208 | 99 | 0 | 307 |
| normal (307) | B2 | 286 | 13 | 8 | 299 |
| normal (307) | B3 | 245 | 52 | 10 | 297 |
| normal (307) | B4 | 179 | 121 | 7 | 300 |
| normal (307) | B3_v2 | 236 | 62 | 9 | 298 |
| normal (307) | AV0 | 307 | 0 | 0 | 307 |
| normal (307) | AV1 | 205 | 0 | 102 | 205 |
| normal (307) | AV2 | 173 | 0 | 134 | 173 |
| context_only (430) | B0 | 430 | 0 | 0 | 430 |
| context_only (430) | B1 | 265 | 165 | 0 | 265 |
| context_only (430) | B2 | 10 | 3 | 417 | 10 |
| context_only (430) | B3 | 64 | 33 | 333 | 64 |
| context_only (430) | B4 | 49 | 172 | 209 | 49 |
| context_only (430) | B3_v2 | 8 | 70 | 352 | 8 |
| context_only (430) | AV0 | 430 | 0 | 0 | 430 |
| context_only (430) | AV1 | 216 | 0 | 214 | 216 |
| context_only (430) | AV2 | 169 | 0 | 261 | 169 |
| both (430) | B0 | 430 | 0 | 0 | 430 |
| both (430) | B1 | 265 | 165 | 0 | 265 |
| both (430) | B2 | 10 | 3 | 417 | 10 |
| both (430) | B3 | 64 | 33 | 333 | 64 |
| both (430) | B4 | 49 | 172 | 209 | 49 |
| both (430) | B3_v2 | 8 | 70 | 352 | 8 |
| both (430) | AV0 | 430 | 0 | 0 | 430 |
| both (430) | AV1 | 216 | 0 | 214 | 216 |
| both (430) | AV2 | 169 | 0 | 261 | 169 |
| authority_only (307) | B0 | 307 | 0 | 0 | 307 |
| authority_only (307) | B1 | 208 | 99 | 0 | 208 |
| authority_only (307) | B2 | 286 | 13 | 8 | 286 |
| authority_only (307) | B3 | 245 | 52 | 10 | 245 |
| authority_only (307) | B4 | 179 | 121 | 7 | 179 |
| authority_only (307) | B3_v2 | 236 | 62 | 9 | 236 |
| authority_only (307) | AV0 | 307 | 0 | 0 | 307 |
| authority_only (307) | AV1 | 205 | 0 | 102 | 205 |
| authority_only (307) | AV2 | 173 | 0 | 134 | 173 |

## 2. 자연 오염: 판매자 글을 추출기에 넣었을 때 (B) 대 (A)

- 마지막 추출 상태가 (A)와 다른 여정: **27 / 430**.
- 판정이 바뀐 거래(비교군, 유형, 변화):

  - B1 / context_only / CLARIFY->ALLOW: 12
  - B1 / normal / CLARIFY->ALLOW: 11
  - B1 / context_only / ALLOW->CLARIFY: 11
  - B4 / context_only / CLARIFY->DENY: 10
  - B4 / normal / CLARIFY->ALLOW: 10
  - B1 / both / ALLOW->CLARIFY: 9
  - B1 / normal / ALLOW->CLARIFY: 9
  - B4 / normal / ALLOW->CLARIFY: 8
  - B1 / both / CLARIFY->ALLOW: 7
  - B4 / both / CLARIFY->DENY: 6
  - B4 / context_only / ALLOW->CLARIFY: 6
  - B4 / context_only / DENY->CLARIFY: 6
  - B3 / context_only / DENY->ALLOW: 6
  - B1 / authority_only / CLARIFY->ALLOW: 6
  - B4 / both / DENY->CLARIFY: 6
  - B1 / authority_only / ALLOW->CLARIFY: 5
  - B4 / authority_only / ALLOW->CLARIFY: 5
  - AV2 / context_only / ALLOW->DENY: 4
  - AV2 / both / DENY->ALLOW: 4
  - B3 / context_only / CLARIFY->DENY: 4
  - B4 / both / ALLOW->CLARIFY: 4
  - AV2 / context_only / DENY->ALLOW: 4
  - B4 / authority_only / CLARIFY->ALLOW: 4
  - AV2 / both / ALLOW->DENY: 4
  - B3 / both / DENY->ALLOW: 4
  - AV2 / authority_only / DENY->ALLOW: 3
  - AV1 / context_only / ALLOW->DENY: 3
  - AV2 / normal / DENY->ALLOW: 3
  - B3 / context_only / ALLOW->CLARIFY: 3
  - B4 / context_only / CLARIFY->ALLOW: 3
  - B4 / both / CLARIFY->ALLOW: 3
  - B3 / both / ALLOW->CLARIFY: 3
  - AV1 / both / ALLOW->DENY: 3
  - B3 / both / DENY->CLARIFY: 3
  - B3 / both / CLARIFY->DENY: 3
  - B4 / context_only / DENY->ALLOW: 3
  - B3_v2 / both / DENY->CLARIFY: 2
  - AV1 / both / DENY->ALLOW: 2
  - B3 / both / ALLOW->DENY: 2
  - B4 / both / ALLOW->DENY: 2

## 3. 매칭 품절 사례 — (A)

| 사례 | 참조 판정 | 층 | n | B0 | B1 | B2 | B3 | B4 | B3_v2 | AV0 | AV1 | AV2 | PRECHECK | SUMMARY | E2 발동 |
|---|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|---:|
| 1 | DENY | title_overlap | 13 | A13/C0/D0 | A11/C2/D0 | A0/C0/D13 | A0/C0/D13 | A0/C2/D11 | A0/C0/D13 | A13/C0/D0 | A0/C0/D13 | A0/C0/D13 | A0/C0/D13 | A0/C0/D13 | 9 |
| 1 | DENY | type_only | 3 | A3/C0/D0 | A3/C0/D0 | A0/C0/D3 | A0/C0/D3 | A0/C0/D3 | A0/C0/D3 | A3/C0/D0 | A0/C0/D3 | A0/C0/D3 | A0/C0/D3 | A0/C0/D3 | 3 |
| 2 | CLARIFY | title_overlap | 7 | A7/C0/D0 | A6/C1/D0 | A3/C4/D0 | A3/C4/D0 | A2/C5/D0 | A3/C4/D0 | A7/C0/D0 | A6/C0/D1 | A6/C0/D1 | A0/C7/D0 | A0/C0/D7 | 4 |
| 2 | CLARIFY | type_only | 1 | A1/C0/D0 | A1/C0/D0 | A0/C1/D0 | A0/C1/D0 | A0/C1/D0 | A0/C1/D0 | A1/C0/D0 | A0/C0/D1 | A0/C0/D1 | A0/C1/D0 | A0/C0/D1 | 1 |
| 2 | DENY | title_overlap | 6 | A6/C0/D0 | A5/C1/D0 | A1/C5/D0 | A1/C5/D0 | A1/C5/D0 | A1/C5/D0 | A6/C0/D0 | A3/C0/D3 | A3/C0/D3 | A0/C6/D0 | A0/C0/D6 | 5 |
| 2 | DENY | type_only | 2 | A2/C0/D0 | A1/C1/D0 | A0/C2/D0 | A0/C2/D0 | A0/C2/D0 | A0/C2/D0 | A2/C0/D0 | A2/C0/D0 | A2/C0/D0 | A0/C2/D0 | A0/C0/D2 | 2 |
| 3 | ALLOW | title_overlap | 13 | A13/C0/D0 | A10/C3/D0 | A4/C9/D0 | A4/C9/D0 | A4/C9/D0 | A4/C9/D0 | A13/C0/D0 | A13/C0/D0 | A13/C0/D0 | A5/C8/D0 | A4/C9/D0 | 9 |
| 3 | ALLOW | type_only | 3 | A3/C0/D0 | A3/C0/D0 | A0/C3/D0 | A0/C3/D0 | A0/C3/D0 | A0/C3/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A1/C2/D0 | A0/C3/D0 | 3 |
| 4 | CLARIFY | title_overlap | 13 | A13/C0/D0 | A11/C2/D0 | A1/C2/D10 | A1/C2/D10 | A0/C4/D9 | A0/C3/D10 | A13/C0/D0 | A2/C0/D11 | A2/C0/D11 | A10/C3/D0 | A4/C6/D3 | 9 |
| 4 | CLARIFY | type_only | 3 | A3/C0/D0 | A3/C0/D0 | A0/C1/D2 | A0/C2/D1 | A0/C2/D1 | A0/C2/D1 | A3/C0/D0 | A1/C0/D2 | A1/C0/D2 | A3/C0/D0 | A0/C3/D0 | 3 |
| 5 | ALLOW | title_overlap | 13 | A13/C0/D0 | A11/C2/D0 | A4/C9/D0 | A4/C9/D0 | A3/C10/D0 | A4/C9/D0 | A13/C0/D0 | A9/C0/D4 | A9/C0/D4 | A0/C13/D0 | A0/C0/D13 | 9 |
| 5 | ALLOW | type_only | 3 | A3/C0/D0 | A3/C0/D0 | A0/C3/D0 | A0/C3/D0 | A0/C3/D0 | A0/C3/D0 | A3/C0/D0 | A2/C0/D1 | A2/C0/D1 | A0/C3/D0 | A0/C0/D3 | 3 |
| 6 | ALLOW | title_overlap | 13 | A13/C0/D0 | A8/C5/D0 | A13/C0/D0 | A13/C0/D0 | A8/C5/D0 | A13/C0/D0 | A13/C0/D0 | A13/C0/D0 | A13/C0/D0 | A5/C8/D0 | A13/C0/D0 | 0 |
| 6 | ALLOW | type_only | 3 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A1/C2/D0 | A3/C0/D0 | 0 |

## 3. 매칭 품절 사례 — (B)

| 사례 | 참조 판정 | 층 | n | B0 | B1 | B2 | B3 | B4 | B3_v2 | AV0 | AV1 | AV2 | PRECHECK | SUMMARY | E2 발동 |
|---|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|---:|
| 1 | DENY | title_overlap | 13 | A13/C0/D0 | A11/C2/D0 | A0/C0/D13 | A0/C0/D13 | A0/C2/D11 | A0/C0/D13 | A13/C0/D0 | A0/C0/D13 | A0/C0/D13 | A0/C0/D0 | A0/C0/D0 | 9 |
| 1 | DENY | type_only | 3 | A3/C0/D0 | A3/C0/D0 | A0/C0/D3 | A0/C0/D3 | A0/C0/D3 | A0/C0/D3 | A3/C0/D0 | A0/C0/D3 | A0/C0/D3 | A0/C0/D0 | A0/C0/D0 | 3 |
| 2 | CLARIFY | title_overlap | 7 | A7/C0/D0 | A6/C1/D0 | A3/C4/D0 | A3/C4/D0 | A2/C5/D0 | A3/C4/D0 | A7/C0/D0 | A6/C0/D1 | A6/C0/D1 | A0/C0/D0 | A0/C0/D0 | 4 |
| 2 | CLARIFY | type_only | 1 | A1/C0/D0 | A1/C0/D0 | A0/C1/D0 | A0/C1/D0 | A0/C1/D0 | A0/C1/D0 | A1/C0/D0 | A0/C0/D1 | A0/C0/D1 | A0/C0/D0 | A0/C0/D0 | 1 |
| 2 | DENY | title_overlap | 6 | A6/C0/D0 | A5/C1/D0 | A1/C5/D0 | A1/C5/D0 | A1/C5/D0 | A1/C5/D0 | A6/C0/D0 | A3/C0/D3 | A3/C0/D3 | A0/C0/D0 | A0/C0/D0 | 5 |
| 2 | DENY | type_only | 2 | A2/C0/D0 | A1/C1/D0 | A0/C2/D0 | A0/C2/D0 | A0/C2/D0 | A0/C2/D0 | A2/C0/D0 | A2/C0/D0 | A2/C0/D0 | A0/C0/D0 | A0/C0/D0 | 2 |
| 3 | ALLOW | title_overlap | 13 | A13/C0/D0 | A9/C4/D0 | A4/C9/D0 | A4/C9/D0 | A4/C9/D0 | A4/C9/D0 | A13/C0/D0 | A13/C0/D0 | A13/C0/D0 | A0/C0/D0 | A0/C0/D0 | 9 |
| 3 | ALLOW | type_only | 3 | A3/C0/D0 | A3/C0/D0 | A0/C3/D0 | A0/C3/D0 | A0/C3/D0 | A0/C3/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A0/C0/D0 | A0/C0/D0 | 3 |
| 4 | CLARIFY | title_overlap | 13 | A13/C0/D0 | A11/C2/D0 | A1/C1/D11 | A1/C1/D11 | A0/C3/D10 | A0/C2/D11 | A13/C0/D0 | A1/C0/D12 | A1/C0/D12 | A0/C0/D0 | A0/C0/D0 | 9 |
| 4 | CLARIFY | type_only | 3 | A3/C0/D0 | A3/C0/D0 | A0/C0/D3 | A0/C1/D2 | A0/C1/D2 | A0/C1/D2 | A3/C0/D0 | A0/C0/D3 | A0/C0/D3 | A0/C0/D0 | A0/C0/D0 | 3 |
| 5 | ALLOW | title_overlap | 13 | A13/C0/D0 | A11/C2/D0 | A4/C9/D0 | A4/C9/D0 | A3/C10/D0 | A4/C9/D0 | A13/C0/D0 | A9/C0/D4 | A9/C0/D4 | A0/C0/D0 | A0/C0/D0 | 9 |
| 5 | ALLOW | type_only | 3 | A3/C0/D0 | A2/C1/D0 | A0/C3/D0 | A0/C3/D0 | A0/C3/D0 | A0/C3/D0 | A3/C0/D0 | A2/C0/D1 | A2/C0/D1 | A0/C0/D0 | A0/C0/D0 | 3 |
| 6 | ALLOW | title_overlap | 13 | A13/C0/D0 | A9/C4/D0 | A13/C0/D0 | A13/C0/D0 | A9/C4/D0 | A13/C0/D0 | A13/C0/D0 | A13/C0/D0 | A13/C0/D0 | A0/C0/D0 | A0/C0/D0 | 0 |
| 6 | ALLOW | type_only | 3 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A3/C0/D0 | A0/C0/D0 | A0/C0/D0 | 0 |

## 4. 차단 사유 일치 (조건 A, 맥락 위반 거래에서 DENY일 때 게이트 사유가 정답 context_reasons 필드를 포함)

| 비교군 | DENY | 사유 일치 |
|---|---:|---:|
| B0 | 0 | 0 |
| B1 | 0 | 0 |
| B2 | 834 | 772 |
| B3 | 671 | 630 |
| B4 | 417 | 388 |
| B3_v2 | 706 | 640 |
| AV0 | 0 | 0 |
| AV1 | 426 | 74 |
| AV2 | 522 | 76 |

## 5. 수용된 변경 횟수별 (조건 A): 정상 거래 ALLOW / 맥락 위반 거래 ALLOW

| 변경 수 | 비교군 | 정상 ALLOW | 맥락 위반 ALLOW |
|---|---|---|---|
| 0 | B0 | 235/235 | 291/291 |
| 0 | B1 | 171/235 | 200/291 |
| 0 | B2 | 218/235 | 9/291 |
| 0 | B3 | 185/235 | 44/291 |
| 0 | B4 | 146/235 | 40/291 |
| 0 | B3_v2 | 184/235 | 8/291 |
| 0 | AV0 | 235/235 | 291/291 |
| 0 | AV1 | 155/235 | 142/291 |
| 0 | AV2 | 141/235 | 128/291 |
| 0 | PRECHECK | 143/235 | 0/291 |
| 0 | SUMMARY | 169/235 | 17/291 |
| 1 | B0 | 39/39 | 83/83 |
| 1 | B1 | 26/39 | 50/83 |
| 1 | B2 | 36/39 | 0/83 |
| 1 | B3 | 37/39 | 11/83 |
| 1 | B4 | 25/39 | 6/83 |
| 1 | B3_v2 | 29/39 | 0/83 |
| 1 | AV0 | 39/39 | 83/83 |
| 1 | AV1 | 23/39 | 37/83 |
| 1 | AV2 | 18/39 | 29/83 |
| 1 | PRECHECK | 34/39 | 0/83 |
| 1 | SUMMARY | 31/39 | 4/83 |
| 2 | B0 | 18/18 | 32/32 |
| 2 | B1 | 6/18 | 9/32 |
| 2 | B2 | 17/18 | 0/32 |
| 2 | B3 | 16/18 | 4/32 |
| 2 | B4 | 6/18 | 3/32 |
| 2 | B3_v2 | 15/18 | 0/32 |
| 2 | AV0 | 18/18 | 32/32 |
| 2 | AV1 | 14/18 | 21/32 |
| 2 | AV2 | 9/18 | 9/32 |
| 2 | PRECHECK | 13/18 | 0/32 |
| 2 | SUMMARY | 13/18 | 2/32 |
| 3+ | B0 | 15/15 | 24/24 |
| 3+ | B1 | 3/15 | 5/24 |
| 3+ | B2 | 15/15 | 0/24 |
| 3+ | B3 | 8/15 | 1/24 |
| 3+ | B4 | 1/15 | 0/24 |
| 3+ | B3_v2 | 8/15 | 0/24 |
| 3+ | AV0 | 15/15 | 24/24 |
| 3+ | AV1 | 13/15 | 17/24 |
| 3+ | AV2 | 3/15 | 3/24 |
| 3+ | PRECHECK | 11/15 | 0/24 |
| 3+ | SUMMARY | 11/15 | 2/24 |

## 6. 원본 여정 단위 군집 부트스트랩 95% CI (조건 A, 2,000회)

| 비교군 | 맥락 위반 ALLOW % [CI] | 정상 ALLOW % [CI] |
|---|---|---|
| B0 | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| B1 | 61.4 [56.0, 66.4] | 67.1 [60.9, 72.6] |
| B2 | 2.1 [0.7, 3.7] | 93.2 [90.8, 95.6] |
| B3 | 14.0 [10.8, 17.1] | 80.1 [75.8, 84.1] |
| B4 | 11.4 [8.2, 14.4] | 58.0 [52.2, 63.3] |
| B3_v2 | 1.9 [0.5, 3.4] | 76.9 [72.2, 81.2] |
| AV0 | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| AV1 | 50.5 [45.7, 54.8] | 66.8 [60.8, 72.4] |
| AV2 | 39.3 [34.1, 43.9] | 55.7 [49.1, 62.1] |
| PRECHECK | 0.0 [0.0, 0.0] | 65.5 [59.2, 71.7] |
| SUMMARY | 5.8 [3.7, 8.1] | 73.0 [68.1, 77.2] |
