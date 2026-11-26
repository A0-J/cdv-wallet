# v4 dev 주입: 검증기 대 '대화를 읽지 않는 지름길' 정답률 (후보 498, 정답 operation_labels)

- 지름길은 dev 안에서 여정 단위로 하나씩 빼고 학습(leave-one-episode-out). eval은 쓰지 않았다. 미지원(Attribute)은 오답으로 센다.

| 방법 | 정답 | 정답률 |
|---|---:|---:|
| 지름길: majority | 211 | 42.4% |
| 지름길: operation+field | 232 | 46.6% |
| 지름길: cited speaker | 284 | 57.0% |
| 지름길: operation+field+speaker | 272 | 54.6% |
| M1 v1 (규칙, PLAN_v3) | 255 | 51.2% |
| M1 v2 (규칙 + 출처 분리) | 260 | 52.2% |
| M1-G 1회 | 391 | 78.5% |
| M1-G 2회 | 387 | 77.7% |
