# P4 계획: v4 dev 통합 실행 (B0–B4, 입력 조건 A/B)

- 작성: 2026-11-26. 연구자 결정: 합성 데이터는 v4로 통일, 판매자 글은 입력 조건 (A)·(B)로 모두 실행, 실행 전 제외 ID와 최종 n 보고.
- 데이터: `C:\ct\external\carttrace_cdv_evaluation_v4` (zip sha256 `a1fbd502df8df0272ce77e9920746bc5f3a586a9b3e049cb01887bab47396eb2`). dev 파일 sha256: episodes `e861435a32ff7a1c63a4309d1f290c941d5ecd61c25c6c5184c30708b244f80c`, transactions `580b2cdaceeb941b81b351004fb27d6e8e0fe450d3295ee540d81d2163febecb`, transaction_gold `af0f401877b07e9359518b55da18dc3051b2951b8110b279f48bccff0739b610`, episode_gold `1486013aeeabea1a4e85cb685a838ba4f1e0c48b2a7db624842e873e3a39af44`, matched_stockout `5e173215f4e0568fad010e08dc4d9ee8b17bac697b172f6be19df076323f1347`.
- 제외: 원본 여정이 이미 본 여정인 2여정(노출 기록) → **430여정 / 1,474거래**. 봉인 표본과 겹침 0 (`exclusion_v4_dev.json`).
- 입력: (A) 쇼핑객·에이전트 턴만 추출기에. (B) source=seller인 tool 턴도 추출기에(에이전트 쪽 문장으로). 두 조건 모두 tool 턴은 M1의 비사용자 문장, catalog `listing_text`는 A-VIP 라벨. checkout.fulfillment / days는 결제 동의 시점 사실. 정답 파일은 채점에만.
- 모델: gpt-6-luna, PLAN_v3와 같은 추출 코드(`cdv/extract.py` `444f55f948f3a7c3c8747abe03fb81bc807bba02ca6fa63c843eb7b0d69ce94b`). 조건마다 여정당 추출 1회를 다섯 비교군이 공유. (B)는 판매자 턴 이후 호출만 새로 과금(같은 요청은 캐시).
- 규칙: `cdv/m1.py` `1a642a2121cce5b68f5adfe8d2491306da9d3ef7962088f945f5f83a970ce160` (단서 명세 반영, 연구자 커밋으로 고정 예정), `eval/integrated/arms.py` `1a8eb291bd43decb4a5be678172a781b2b1f5a3f883dcf6dda6cb1a3449fdab3`, `cdv/v2/scope.py` `9650bdfb1d117aa0c768c4c4aa821c7fe467e667c016b81d4aff4a4c88dc347a`, 실행기 `eval/extdata/run_ext.py` `4898153da2a34687e0c539a213d2561423bbe4348959fa18c6ab6317bf67dec5`.
- 호출 수: 드라이런 하한 (A) 1,397, (B) 1,397(입력 토큰 약 1.5% 더 많음). 인자 생성 포함 추정 (A) 약 2,200, (B) 추가 약 700–900.
- 비용: 추정 (A)+(B) 약 $0.30–0.40. **상한 $0.60** (같은 원장 누적: A `--budget 0.35`, B `--budget 0.60`).
- 채점: transaction_gold.expected_checkout 대 비교군 판정(ALLOW/CLARIFY/DENY 분리). 거래 유형(정상, 맥락 위반, 요청 무결성 위반, 복합)별. (B)에서 추출기가 판매자 글에 속은 사례 수 = (B) 상태가 (A) 상태와 다르고 그 차이가 판매자 턴 이후에 생긴 여정. 매칭 품절 뷰(쌍당 6건, reference_verdict, pair_similarity 층)와 권한 축은 따로 보고.
- 알려진 M2 표현력 한계(v4 dev, 정답 조건 기준 비교 `results/v4check_20261126/CART_COMPARE_dev.md`): 수수료 포함 총액(가격 214건 놓침), 허용 대안·품절 대체(수량 204건 과잉). 이 계획에서는 고치지 않는다.
- 실행 명령(같은 원장 누적 상한): `run_ext.py --data C:/ct/external/carttrace_cdv_evaluation_v4 --name v4 --split dev --with-matched --budget 0.35` → `... --with-matched --seller-to-extractor --budget 0.60`. 매칭 96건은 같은 추출을 공유해 추가 호출이 없다.
- 무과금 연결 시험(빈 추출): 거래 60건 + 매칭 30건 오류 0. 플랫폼 tool 턴의 재고 0을 플랫폼 증거로 쓴다(매칭 30건 중 7건).
