# 짝지은 비교 (validation 개발 분할, `dev_rows_arms2.jsonl`, 모델 호출 0)

- 차단 = CLARIFY 또는 DENY. pay_viol = 정답 조건을 넣은 U 기준이 막는 여정(우리 게이트로 정의됨).
- AV1과 B2는 같은 추출 상태(t 직전 마지막 상태)를 쓴다. 차이는 검사기(PLAN_v3 장바구니 검사 대 M2 게이트)뿐이다.
- AV2는 상태를 누적(지우지 않음)하고 검사기는 AV1과 같다. 그래서 AV2 대 B2는 상태 구성과 검사기가 함께 다르다.

## AV1 대 B2 — pay_viol (n=30)

- 둘 다 차단 8, AV1만 0, B2만 8, 둘 다 통과 14. McNemar 정확 p = 0.0078.

| 여정 | AV1 | AV1 차단 요소 | B2 | B2 차단 요소 |
|---|---|---|---|---|
| `d51c8e93` | ALLOW | - | DENY | 총액(수수료 포함) |
| `e6abf5d8` | ALLOW | - | DENY | 총액(수수료 포함) |
| `6106710d` | ALLOW | - | DENY | 총액(수수료 포함) |
| `4df01dd7` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `963050a4` | ALLOW | - | DENY | 총액(수수료 포함) |
| `d82dbb86` | ALLOW | - | DENY | 총액(수수료 포함) |
| `bc477a35` | ALLOW | - | DENY | 총액(수수료 포함) |
| `1e414988` | ALLOW | - | DENY | 총액(수수료 포함) |

- B2만 막은 8건의 차단 요소: 총액(수수료 포함) 7, 정보 부족(확인) 1

## AV1 대 B2 — legit (n=235)

- 둘 다 차단 18, AV1만 2, B2만 10, 둘 다 통과 205. McNemar 정확 p = 0.0386.

| 여정 | AV1 | AV1 차단 요소 | B2 | B2 차단 요소 |
|---|---|---|---|---|
| `4e86c338` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `b80b1048` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `b80b1048` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `cee0a64c` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `dc6918a2` | ALLOW | - | DENY | 총액(수수료 포함) |
| `bbde542e` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `5136bee1` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `2b7da304` | ALLOW | - | DENY | 총액(수수료 포함) |
| `94f0f75f` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `94f0f75f` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `9f3d3de6` | DENY | 브랜드 | ALLOW | - |
| `d462e938` | DENY | 브랜드 | ALLOW | - |

- B2만 막은 10건의 차단 요소: 정보 부족(확인) 8, 총액(수수료 포함) 2

## AV2 대 B2 — pay_viol (n=30)

- 둘 다 차단 11, AV2만 1, B2만 5, 둘 다 통과 13. McNemar 정확 p = 0.2188.

| 여정 | AV2 | AV2 차단 요소 | B2 | B2 차단 요소 |
|---|---|---|---|---|
| `e6abf5d8` | ALLOW | - | DENY | 총액(수수료 포함) |
| `6106710d` | ALLOW | - | DENY | 총액(수수료 포함) |
| `963050a4` | ALLOW | - | DENY | 총액(수수료 포함) |
| `d82dbb86` | ALLOW | - | DENY | 총액(수수료 포함) |
| `1e414988` | ALLOW | - | DENY | 총액(수수료 포함) |
| `eefb14af` | DENY | 묶음 구성 | ALLOW | - |

- B2만 막은 5건의 차단 요소: 총액(수수료 포함) 5

## AV2 대 B2 — legit (n=235)

- 둘 다 차단 20, AV2만 8, B2만 8, 둘 다 통과 199. McNemar 정확 p = 1.0.

| 여정 | AV2 | AV2 차단 요소 | B2 | B2 차단 요소 |
|---|---|---|---|---|
| `4e86c338` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `cee0a64c` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `dc6918a2` | ALLOW | - | DENY | 총액(수수료 포함) |
| `bbde542e` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `5136bee1` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `2b7da304` | ALLOW | - | DENY | 총액(수수료 포함) |
| `94f0f75f` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `94f0f75f` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `9f3d3de6` | DENY | 브랜드 | ALLOW | - |
| `52121a2c` | DENY | 묶음 구성 | ALLOW | - |
| `cecca788` | DENY | 묶음 구성 | ALLOW | - |
| `d462e938` | DENY | 브랜드 | ALLOW | - |
| `823802e9` | DENY | 묶음 구성 | ALLOW | - |
| `f88efc99` | DENY | 브랜드 | ALLOW | - |
| `56ea77ef` | DENY | 브랜드 | ALLOW | - |
| `9e3df0a7` | DENY | 브랜드 | ALLOW | - |

- B2만 막은 8건의 차단 요소: 정보 부족(확인) 6, 총액(수수료 포함) 2

## B2 대 B3 — pay_viol (n=30)

- 둘 다 차단 14, B2만 2, B3만 3, 둘 다 통과 11. McNemar 정확 p = 1.0.

| 여정 | B2 | B2 차단 요소 | B3 | B3 차단 요소 |
|---|---|---|---|---|
| `8a1a35bb` | ALLOW | - | CLARIFY | 브랜드, M1 확인 |
| `eefb14af` | ALLOW | - | CLARIFY | 수량, M1 확인 |
| `17575864` | ALLOW | - | DENY | 총액(수수료 포함) |
| `d51c8e93` | DENY | 총액(수수료 포함) | ALLOW | - |
| `89f6155a` | DENY | 수량 | ALLOW | - |

- B3만 막은 3건의 차단 요소: 총액(수수료 포함) 1, 브랜드, M1 확인 1, 수량, M1 확인 1

## B2 대 B3 — legit (n=235)

- 둘 다 차단 25, B2만 3, B3만 17, 둘 다 통과 190. McNemar 정확 p = 0.0026.

| 여정 | B2 | B2 차단 요소 | B3 | B3 차단 요소 |
|---|---|---|---|---|
| `3fed61fc` | ALLOW | - | CLARIFY | 선택 불일치, 수량 |
| `52121a2c` | ALLOW | - | DENY | 묶음 구성 |
| `cecca788` | ALLOW | - | DENY | 브랜드, 묶음 구성 |
| `1e3f1342` | ALLOW | - | CLARIFY | 기타:EVIDENCE_MISSING |
| `7871e27e` | ALLOW | - | CLARIFY | 선택 불일치, 수량 |
| `80ee3297` | ALLOW | - | CLARIFY | 선택 불일치, 수량 |
| `120f502c` | ALLOW | - | CLARIFY | 선택 불일치, 수량 |
| `9e392b95` | ALLOW | - | CLARIFY | 선택 불일치, 수량 |
| `961aa992` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `316a11a0` | ALLOW | - | CLARIFY | 선택 불일치, 수량 |
| `028379d6` | ALLOW | - | CLARIFY | 선택 불일치, 수량 |
| `49736d8d` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `9961a5fa` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `edde105b` | ALLOW | - | CLARIFY | 선택 불일치, 수량, M1 확인 |
| `56ea77ef` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `9e3df0a7` | ALLOW | - | DENY | 브랜드 |
| `03e5635a` | ALLOW | - | CLARIFY | 수량, M1 확인 |
| `dc6918a2` | DENY | 총액(수수료 포함) | ALLOW | - |
| `5136bee1` | CLARIFY | 정보 부족(확인) | ALLOW | - |
| `2b7da304` | DENY | 총액(수수료 포함) | ALLOW | - |

- B3만 막은 17건의 차단 요소: 선택 불일치, 수량 7, 정보 부족(확인) 4, 브랜드, 묶음 구성 1, 기타:EVIDENCE_MISSING 1, 선택 불일치, 수량, M1 확인 1, 수량, M1 확인 1, 묶음 구성 1, 브랜드 1

## B3 대 B4 — pay_viol (n=30)

- 둘 다 차단 17, B3만 0, B4만 7, 둘 다 통과 6. McNemar 정확 p = 0.0156.

| 여정 | B3 | B3 차단 요소 | B4 | B4 차단 요소 |
|---|---|---|---|---|
| `da0d6fe7` | ALLOW | - | CLARIFY | M1 확인 |
| `d51c8e93` | ALLOW | - | CLARIFY | M1 확인 |
| `f0130b35` | ALLOW | - | CLARIFY | M1 확인 |
| `5b397f8b` | ALLOW | - | CLARIFY | M1 확인 |
| `f3b1f2c0` | ALLOW | - | CLARIFY | M1 확인 |
| `bfc46591` | ALLOW | - | CLARIFY | M1 확인 |
| `6347dc27` | ALLOW | - | CLARIFY | M1 확인 |

- B4만 막은 7건의 차단 요소: M1 확인 7

## B3 대 B4 — legit (n=235)

- 둘 다 차단 42, B3만 0, B4만 113, 둘 다 통과 80. McNemar 정확 p = 0.0.

| 여정 | B3 | B3 차단 요소 | B4 | B4 차단 요소 |
|---|---|---|---|---|
| `9f3d3de6` | ALLOW | - | CLARIFY | M1 확인 |
| `bcd894b9` | ALLOW | - | CLARIFY | M1 확인 |
| `9b0e81db` | ALLOW | - | CLARIFY | M1 확인 |
| `72afdc29` | ALLOW | - | CLARIFY | M1 확인 |
| `2ec7f251` | ALLOW | - | CLARIFY | M1 확인 |
| `5ec838c7` | ALLOW | 조건 조항 | CLARIFY | 조건 조항, M1 확인 |
| `37c2bbe4` | ALLOW | - | CLARIFY | M1 확인 |
| `a8460af5` | ALLOW | - | CLARIFY | M1 확인 |
| `70bc7d91` | ALLOW | - | CLARIFY | M1 확인 |
| `0c63937a` | ALLOW | - | CLARIFY | M1 확인 |
| `ed997c1e` | ALLOW | - | CLARIFY | M1 확인 |
| `ed997c1e` | ALLOW | - | CLARIFY | M1 확인 |
| `62630669` | ALLOW | - | CLARIFY | M1 확인 |
| `815eb540` | ALLOW | - | CLARIFY | M1 확인 |
| `a73c06c7` | ALLOW | 조건 조항 | CLARIFY | 조건 조항, M1 확인 |
| `ec09529a` | ALLOW | - | CLARIFY | M1 확인 |
| `38912e4c` | ALLOW | - | CLARIFY | M1 확인 |
| `fa107271` | ALLOW | - | CLARIFY | M1 확인 |
| `1d8a5bc0` | ALLOW | - | CLARIFY | M1 확인 |
| `3aeec12c` | ALLOW | - | CLARIFY | M1 확인 |
| `4c41084f` | ALLOW | - | CLARIFY | M1 확인 |
| `551a9c22` | ALLOW | - | CLARIFY | M1 확인 |
| `e7adae0e` | ALLOW | - | CLARIFY | M1 확인 |
| `b75c6bd7` | ALLOW | - | CLARIFY | M1 확인 |
| `cff097f4` | ALLOW | - | CLARIFY | M1 확인 |
| `5a05e2fd` | ALLOW | - | CLARIFY | M1 확인 |
| `c23895e5` | ALLOW | - | CLARIFY | M1 확인 |
| `0a20b244` | ALLOW | - | CLARIFY | M1 확인 |
| `0a20b244` | ALLOW | - | CLARIFY | M1 확인 |
| `4d62dcb3` | ALLOW | - | CLARIFY | M1 확인 |
| `cf3d5f28` | ALLOW | - | CLARIFY | M1 확인 |
| `ce41ac64` | ALLOW | - | CLARIFY | M1 확인 |
| `32416fcb` | ALLOW | - | CLARIFY | M1 확인 |
| `e2f035ad` | ALLOW | - | CLARIFY | M1 확인 |
| `b56eae54` | ALLOW | - | CLARIFY | M1 확인 |
| `3ca9f27e` | ALLOW | - | CLARIFY | M1 확인 |
| `13fc0a3a` | ALLOW | - | CLARIFY | M1 확인 |
| `5ff27b5c` | ALLOW | - | CLARIFY | M1 확인 |
| `60828899` | ALLOW | - | CLARIFY | M1 확인 |
| `38b4bea1` | ALLOW | - | CLARIFY | M1 확인 |
| `944165b8` | ALLOW | - | CLARIFY | M1 확인 |
| `eddd98b6` | ALLOW | - | CLARIFY | M1 확인 |
| `232db809` | ALLOW | - | CLARIFY | M1 확인 |
| `c129e7fe` | ALLOW | - | CLARIFY | M1 확인 |
| `72af7bd7` | ALLOW | - | CLARIFY | M1 확인 |
| `06eb8cf4` | ALLOW | - | CLARIFY | M1 확인 |
| `5813f421` | ALLOW | - | CLARIFY | M1 확인 |
| `94101ff6` | ALLOW | - | CLARIFY | M1 확인 |
| `958cf614` | ALLOW | - | CLARIFY | M1 확인 |
| `e2ffd5dc` | ALLOW | - | CLARIFY | M1 확인 |
| `f269b473` | ALLOW | - | CLARIFY | M1 확인 |
| `e88e0699` | ALLOW | - | CLARIFY | M1 확인 |
| `45696b94` | ALLOW | - | CLARIFY | M1 확인 |
| `bb9edfd4` | ALLOW | - | CLARIFY | M1 확인 |
| `f5d63a6b` | ALLOW | - | CLARIFY | M1 확인 |
| `3d3d9c8d` | ALLOW | - | CLARIFY | M1 확인 |
| `49545dd9` | ALLOW | - | CLARIFY | M1 확인 |
| `773ebda8` | ALLOW | - | CLARIFY | M1 확인 |
| `5a3ad29e` | ALLOW | - | CLARIFY | M1 확인 |
| `3618c088` | ALLOW | - | CLARIFY | M1 확인 |
| `823802e9` | ALLOW | - | CLARIFY | M1 확인 |
| `54911eb7` | ALLOW | - | CLARIFY | M1 확인 |
| `bc0a8706` | ALLOW | - | CLARIFY | M1 확인 |
| `bf4ec166` | ALLOW | - | CLARIFY | M1 확인 |
| `030f4140` | ALLOW | - | CLARIFY | M1 확인 |
| `4d6ad0f0` | ALLOW | - | CLARIFY | M1 확인 |
| `632ed6f3` | ALLOW | - | CLARIFY | M1 확인 |
| `cd81a767` | ALLOW | - | CLARIFY | M1 확인 |
| `df41c5ed` | ALLOW | - | CLARIFY | M1 확인 |
| `13ca06c1` | ALLOW | - | CLARIFY | M1 확인 |
| `d371e339` | ALLOW | 조건 조항 | CLARIFY | 조건 조항, M1 확인 |
| `52165842` | ALLOW | - | CLARIFY | M1 확인 |
| `957a2651` | ALLOW | - | CLARIFY | M1 확인 |
| `f9e74180` | ALLOW | - | CLARIFY | M1 확인 |
| `5136bee1` | ALLOW | - | CLARIFY | M1 확인 |
| `deabd1fc` | ALLOW | - | CLARIFY | M1 확인 |
| `b306819f` | ALLOW | 조건 조항 | CLARIFY | 조건 조항, M1 확인 |
| `faccef72` | ALLOW | - | CLARIFY | M1 확인 |
| `faa30fde` | ALLOW | - | CLARIFY | M1 확인 |
| `4314ecf8` | ALLOW | - | CLARIFY | M1 확인 |
| `0372b9ef` | ALLOW | - | CLARIFY | M1 확인 |
| `87c6705f` | ALLOW | - | CLARIFY | M1 확인 |
| `fc8bd5ce` | ALLOW | - | CLARIFY | M1 확인 |
| `2ffc90fb` | ALLOW | - | CLARIFY | M1 확인 |
| `659a672e` | ALLOW | - | CLARIFY | M1 확인 |
| `3c63065d` | ALLOW | - | CLARIFY | M1 확인 |
| `fa6408c5` | ALLOW | - | CLARIFY | M1 확인 |
| `e1f2bb23` | ALLOW | - | CLARIFY | M1 확인 |
| `7865b5f2` | ALLOW | - | CLARIFY | M1 확인 |
| `27ec435e` | ALLOW | - | CLARIFY | M1 확인 |
| `dbe54f1c` | ALLOW | - | CLARIFY | M1 확인 |
| `d4cea795` | ALLOW | 조건 조항 | CLARIFY | 조건 조항, M1 확인 |
| `7ec89779` | ALLOW | - | CLARIFY | M1 확인 |
| `a53b2317` | ALLOW | - | CLARIFY | M1 확인 |
| `f88efc99` | ALLOW | - | CLARIFY | M1 확인 |
| `5eef2cbb` | ALLOW | - | CLARIFY | M1 확인 |
| `b3b5e01d` | ALLOW | - | CLARIFY | M1 확인 |
| `f1fc906a` | ALLOW | - | CLARIFY | M1 확인 |
| `63114935` | ALLOW | - | CLARIFY | M1 확인 |
| `551375e9` | ALLOW | - | CLARIFY | M1 확인 |
| `f9eb1fdb` | ALLOW | - | CLARIFY | M1 확인 |
| `1b709005` | ALLOW | - | CLARIFY | M1 확인 |
| `06ca39ab` | ALLOW | - | CLARIFY | M1 확인 |
| `2b7da304` | ALLOW | - | CLARIFY | M1 확인 |
| `449d494e` | ALLOW | - | CLARIFY | M1 확인 |
| `5346b8f8` | ALLOW | - | CLARIFY | M1 확인 |
| `c7399c0e` | ALLOW | - | CLARIFY | M1 확인 |
| `ff4f7a43` | ALLOW | - | CLARIFY | M1 확인 |
| `8e366c69` | ALLOW | - | CLARIFY | M1 확인 |
| `41e1d70f` | ALLOW | - | CLARIFY | M1 확인 |
| `7bd693a5` | ALLOW | - | CLARIFY | M1 확인 |
| `7519332f` | ALLOW | - | CLARIFY | M1 확인 |
| `3381fce5` | ALLOW | - | CLARIFY | M1 확인 |

- B4만 막은 113건의 차단 요소: M1 확인 108, 조건 조항, M1 확인 5

