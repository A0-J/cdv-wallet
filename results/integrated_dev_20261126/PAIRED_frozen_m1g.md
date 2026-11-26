# 짝지은 비교 (validation 개발 분할, `dev_rows_frozen_m1g.jsonl`, 모델 호출 0)

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

- 둘 다 차단 18, AV1만 2, B2만 26, 둘 다 통과 189. McNemar 정확 p = 0.0.

| 여정 | AV1 | AV1 차단 요소 | B2 | B2 차단 요소 |
|---|---|---|---|---|
| `bcd894b9` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `62630669` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `815eb540` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `facafe33` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `fa107271` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `3aeec12c` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `4e86c338` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `b80b1048` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `b80b1048` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `b75c6bd7` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `5a05e2fd` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `13fc0a3a` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `cee0a64c` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `dc6918a2` | ALLOW | - | DENY | 총액(수수료 포함) |
| `49e2cb3a` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `b1a131b4` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `cd81a767` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `bbde542e` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `5136bee1` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `dbe54f1c` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `a93cd2d6` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `2b7da304` | ALLOW | - | DENY | 총액(수수료 포함) |
| `94f0f75f` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `94f0f75f` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `0328f8dd` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `7234acfc` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `9f3d3de6` | DENY | 브랜드 | ALLOW | - |
| `d462e938` | DENY | 브랜드 | ALLOW | - |

- B2만 막은 26건의 차단 요소: 동의 시점 미검증(확인) 16, 정보 부족(확인) 8, 총액(수수료 포함) 2

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

- 둘 다 차단 20, AV2만 8, B2만 24, 둘 다 통과 183. McNemar 정확 p = 0.007.

| 여정 | AV2 | AV2 차단 요소 | B2 | B2 차단 요소 |
|---|---|---|---|---|
| `bcd894b9` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `62630669` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `815eb540` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `facafe33` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `fa107271` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `3aeec12c` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `4e86c338` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `b75c6bd7` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `5a05e2fd` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `13fc0a3a` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `cee0a64c` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `dc6918a2` | ALLOW | - | DENY | 총액(수수료 포함) |
| `49e2cb3a` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `b1a131b4` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `cd81a767` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `bbde542e` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `5136bee1` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `dbe54f1c` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `a93cd2d6` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `2b7da304` | ALLOW | - | DENY | 총액(수수료 포함) |
| `94f0f75f` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `94f0f75f` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `0328f8dd` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `7234acfc` | ALLOW | - | CLARIFY | 동의 시점 미검증(확인) |
| `9f3d3de6` | DENY | 브랜드 | ALLOW | - |
| `52121a2c` | DENY | 묶음 구성 | ALLOW | - |
| `cecca788` | DENY | 묶음 구성 | ALLOW | - |
| `d462e938` | DENY | 브랜드 | ALLOW | - |
| `823802e9` | DENY | 묶음 구성 | ALLOW | - |
| `f88efc99` | DENY | 브랜드 | ALLOW | - |
| `56ea77ef` | DENY | 브랜드 | ALLOW | - |
| `9e3df0a7` | DENY | 브랜드 | ALLOW | - |

- B2만 막은 24건의 차단 요소: 동의 시점 미검증(확인) 16, 정보 부족(확인) 6, 총액(수수료 포함) 2

## B2 대 B3 — pay_viol (n=30)

- 둘 다 차단 13, B2만 3, B3만 2, 둘 다 통과 12. McNemar 정확 p = 1.0.

| 여정 | B2 | B2 차단 요소 | B3 | B3 차단 요소 |
|---|---|---|---|---|
| `eefb14af` | ALLOW | - | DENY | 수량, 묶음 구성, 선택 상품 포함 |
| `17575864` | ALLOW | - | DENY | 총액(수수료 포함) |
| `6106710d` | DENY | 총액(수수료 포함) | ALLOW | - |
| `1e414988` | DENY | 총액(수수료 포함) | ALLOW | - |
| `89f6155a` | DENY | 수량 | ALLOW | - |

- B3만 막은 2건의 차단 요소: 총액(수수료 포함) 1, 수량, 묶음 구성, 선택 상품 포함 1

## B2 대 B3 — legit (n=235)

- 둘 다 차단 19, B2만 25, B3만 13, 둘 다 통과 178. McNemar 정확 p = 0.073.

| 여정 | B2 | B2 차단 요소 | B3 | B3 차단 요소 |
|---|---|---|---|---|
| `3fed61fc` | ALLOW | - | CLARIFY | 선택 불일치, 수량 |
| `52121a2c` | ALLOW | - | DENY | 묶음 구성 |
| `cecca788` | ALLOW | - | DENY | 묶음 구성 |
| `1e3f1342` | ALLOW | - | CLARIFY | 기타:EVIDENCE_MISSING |
| `7871e27e` | ALLOW | - | CLARIFY | 선택 불일치, 수량 |
| `80ee3297` | ALLOW | - | CLARIFY | 선택 불일치, 수량 |
| `120f502c` | ALLOW | - | CLARIFY | 선택 불일치, 수량 |
| `9e392b95` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `961aa992` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `316a11a0` | ALLOW | - | CLARIFY | 선택 불일치, 수량 |
| `028379d6` | ALLOW | - | CLARIFY | 선택 불일치, 수량 |
| `49736d8d` | ALLOW | - | CLARIFY | 정보 부족(확인) |
| `9961a5fa` | ALLOW | - | CLARIFY | M1 확인 |
| `56637d5b` | DENY | 수량 | ALLOW | 조건 조항 |
| `7f49149c` | DENY | 묶음 구성 | ALLOW | - |
| `bcd894b9` | CLARIFY | 동의 시점 미검증(확인) | ALLOW | - |
| `d93c2cef` | CLARIFY | 정보 부족(확인) | ALLOW | - |
| `815eb540` | CLARIFY | 동의 시점 미검증(확인) | ALLOW | - |
| `facafe33` | CLARIFY | 동의 시점 미검증(확인) | ALLOW | - |
| `fa107271` | CLARIFY | 동의 시점 미검증(확인) | ALLOW | - |
| `4e86c338` | CLARIFY | 정보 부족(확인) | ALLOW | - |
| `b80b1048` | CLARIFY | 정보 부족(확인) | ALLOW | - |
| `5a05e2fd` | CLARIFY | 동의 시점 미검증(확인) | ALLOW | - |
| `8542bb08` | DENY | 브랜드 | ALLOW | - |
| `e72f843e` | DENY | 묶음 구성 | ALLOW | - |
| `515efb9c` | CLARIFY | 정보 부족(확인) | ALLOW | - |
| `2ecd7531` | DENY | 수량 | ALLOW | 조건 조항 |
| `7c40b1c5` | DENY | 수량 | ALLOW | - |
| `58d2a92e` | DENY | 묶음 구성 | ALLOW | - |
| `dbe54f1c` | CLARIFY | 동의 시점 미검증(확인) | ALLOW | - |
| `414043e9` | CLARIFY | 정보 부족(확인) | ALLOW | - |
| `a93cd2d6` | CLARIFY | 동의 시점 미검증(확인) | ALLOW | - |
| `2b7da304` | DENY | 총액(수수료 포함) | ALLOW | - |
| `94f0f75f` | CLARIFY | 정보 부족(확인) | ALLOW | 조건 조항 |
| `94f0f75f` | CLARIFY | 정보 부족(확인) | ALLOW | 조건 조항 |
| `da8fbcbf` | DENY | 브랜드 | ALLOW | - |
| `da8fbcbf` | DENY | 브랜드 | ALLOW | - |
| `5fa9ab8a` | CLARIFY | 정보 부족(확인) | ALLOW | - |

- B3만 막은 13건의 차단 요소: 선택 불일치, 수량 6, 정보 부족(확인) 3, 묶음 구성 2, M1 확인 1, 기타:EVIDENCE_MISSING 1

## B3 대 B4 — pay_viol (n=30)

- 둘 다 차단 15, B3만 0, B4만 6, 둘 다 통과 9. McNemar 정확 p = 0.0312.

| 여정 | B3 | B3 차단 요소 | B4 | B4 차단 요소 |
|---|---|---|---|---|
| `8a1a35bb` | ALLOW | - | CLARIFY | M1 확인 |
| `da0d6fe7` | ALLOW | - | CLARIFY | M1 확인 |
| `f0130b35` | ALLOW | - | CLARIFY | M1 확인 |
| `6106710d` | ALLOW | - | CLARIFY | M1 확인 |
| `89f6155a` | ALLOW | - | CLARIFY | M1 확인 |
| `6347dc27` | ALLOW | - | CLARIFY | M1 확인 |

- B4만 막은 6건의 차단 요소: M1 확인 6

## B3 대 B4 — legit (n=235)

- 둘 다 차단 32, B3만 0, B4만 57, 둘 다 통과 146. McNemar 정확 p = 0.0.

| 여정 | B3 | B3 차단 요소 | B4 | B4 차단 요소 |
|---|---|---|---|---|
| `7f49149c` | ALLOW | - | CLARIFY | M1 확인 |
| `72afdc29` | ALLOW | - | CLARIFY | M1 확인 |
| `d93c2cef` | ALLOW | - | CLARIFY | M1 확인 |
| `2ec7f251` | ALLOW | - | CLARIFY | M1 확인 |
| `37c2bbe4` | ALLOW | - | CLARIFY | M1 확인 |
| `70bc7d91` | ALLOW | - | CLARIFY | M1 확인 |
| `ed997c1e` | ALLOW | - | CLARIFY | M1 확인 |
| `ed997c1e` | ALLOW | - | CLARIFY | M1 확인 |
| `ec09529a` | ALLOW | - | CLARIFY | M1 확인 |
| `fa107271` | ALLOW | - | CLARIFY | M1 확인 |
| `4e86c338` | ALLOW | - | CLARIFY | M1 확인 |
| `b80b1048` | ALLOW | - | CLARIFY | M1 확인 |
| `e7adae0e` | ALLOW | - | CLARIFY | M1 확인 |
| `5a05e2fd` | ALLOW | - | CLARIFY | M1 확인 |
| `c23895e5` | ALLOW | - | CLARIFY | M1 확인 |
| `c105d6d5` | ALLOW | - | CLARIFY | M1 확인 |
| `ce41ac64` | ALLOW | - | CLARIFY | M1 확인 |
| `e72f843e` | ALLOW | - | CLARIFY | M1 확인 |
| `5ff27b5c` | ALLOW | - | CLARIFY | M1 확인 |
| `38b4bea1` | ALLOW | - | CLARIFY | M1 확인 |
| `232db809` | ALLOW | - | CLARIFY | M1 확인 |
| `c129e7fe` | ALLOW | - | CLARIFY | M1 확인 |
| `a95bd05b` | ALLOW | - | CLARIFY | M1 확인 |
| `e2ffd5dc` | ALLOW | - | CLARIFY | M1 확인 |
| `e88e0699` | ALLOW | - | CLARIFY | M1 확인 |
| `45696b94` | ALLOW | - | CLARIFY | M1 확인 |
| `bb9edfd4` | ALLOW | - | CLARIFY | M1 확인 |
| `f5d63a6b` | ALLOW | - | CLARIFY | M1 확인 |
| `3d3d9c8d` | ALLOW | - | CLARIFY | M1 확인 |
| `823802e9` | ALLOW | - | CLARIFY | M1 확인 |
| `030f4140` | ALLOW | - | CLARIFY | M1 확인 |
| `761ebf29` | ALLOW | - | CLARIFY | M1 확인 |
| `42447cfe` | ALLOW | - | CLARIFY | M1 확인 |
| `2afd24f5` | ALLOW | - | CLARIFY | M1 확인 |
| `055e193b` | ALLOW | - | CLARIFY | M1 확인 |
| `51ed4588` | ALLOW | - | CLARIFY | M1 확인 |
| `f9e74180` | ALLOW | - | CLARIFY | M1 확인 |
| `09fa0e35` | ALLOW | - | CLARIFY | M1 확인 |
| `faccef72` | ALLOW | - | CLARIFY | M1 확인 |
| `d02244b8` | ALLOW | - | CLARIFY | M1 확인 |
| `fc8bd5ce` | ALLOW | - | CLARIFY | M1 확인 |
| `659a672e` | ALLOW | - | CLARIFY | M1 확인 |
| `3c63065d` | ALLOW | - | CLARIFY | M1 확인 |
| `7ec89779` | ALLOW | - | CLARIFY | M1 확인 |
| `5eef2cbb` | ALLOW | - | CLARIFY | M1 확인 |
| `63114935` | ALLOW | - | CLARIFY | M1 확인 |
| `551375e9` | ALLOW | - | CLARIFY | M1 확인 |
| `1b709005` | ALLOW | - | CLARIFY | M1 확인 |
| `a93cd2d6` | ALLOW | - | CLARIFY | M1 확인 |
| `449d494e` | ALLOW | - | CLARIFY | M1 확인 |
| `da8fbcbf` | ALLOW | - | CLARIFY | M1 확인 |
| `5346b8f8` | ALLOW | - | CLARIFY | M1 확인 |
| `fdc1bfa3` | ALLOW | - | CLARIFY | M1 확인 |
| `ff4f7a43` | ALLOW | - | CLARIFY | M1 확인 |
| `6b6b16d3` | ALLOW | - | CLARIFY | M1 확인 |
| `815657b7` | ALLOW | - | CLARIFY | M1 확인 |
| `41e1d70f` | ALLOW | - | CLARIFY | M1 확인 |

- B4만 막은 57건의 차단 요소: M1 확인 57

