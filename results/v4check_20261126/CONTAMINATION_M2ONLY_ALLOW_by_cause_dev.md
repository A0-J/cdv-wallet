# 결함 주입: M2 Only 부당 허용 61건의 원인 (proposed_invalid_operations 항목별 cause, v4 dev)

- 맥락 위반 거래 430건 중 M2 Only ALLOW 61건. 이 결과는 '오염이 일어났을 때의 피해 상한'이다(주입 경로, 생성 데이터).

## 거래 단위: 그 여정의 부당 후보 원인

| 원인 | 거래 |
|---|---:|
| 추출 오류 | 22 |
| 요약 오류 | 21 |
| 가정 질문 | 13 |
| 판매자 글 | 5 |

## 부당 후보 연산 단위: 원인 × 연산 × 필드

| 원인 | 연산 | 필드 | 건수 |
|---|---|---|---:|
| 요약 오류 | REVOKE | Deadline | 7 |
| 추출 오류 | REVOKE | Deadline | 6 |
| 추출 오류 | OVERRIDE | Quantity | 5 |
| 추출 오류 | REVOKE | Fulfillment | 5 |
| 추출 오류 | REVOKE | Price | 5 |
| 가정 질문 | RELAX | Price | 4 |
| 가정 질문 | OVERRIDE | Fulfillment | 4 |
| 요약 오류 | OVERRIDE | Fulfillment | 3 |
| 요약 오류 | REVOKE | Fulfillment | 3 |
| 요약 오류 | OVERRIDE | Quantity | 3 |
| 요약 오류 | RELAX | Price | 3 |
| 가정 질문 | REVOKE | Deadline | 2 |
| 가정 질문 | REVOKE | Fulfillment | 2 |
| 요약 오류 | REVOKE | Price | 2 |
| 판매자 글 | REVOKE | Deadline | 2 |
| 판매자 글 | OVERRIDE | Quantity | 2 |
| 판매자 글 | OVERRIDE | Fulfillment | 1 |
| 추출 오류 | RELAX | Price | 1 |
| 가정 질문 | OVERRIDE | Quantity | 1 |

## 참고: 맥락 위반 거래 전체의 부당 후보 원인 분포

- 추출 오류: 61
- 요약 오류: 52
- 판매자 글: 32
- 가정 질문: 26
