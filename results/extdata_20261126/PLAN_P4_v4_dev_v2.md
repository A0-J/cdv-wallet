# P4 계획 (재작성): v4 dev 통합 실행 — 입력 조건 (A)·(B), 추가 비교군 포함

- 작성: 2026-11-26. 연구자 일괄 승인(“계획 sha를 보고하고 바로 실행, 상한 $0.60”). 이전 판 `PLAN_P4_v4_dev.md`(sha `575fc845…`)를 대체한다(이전 판은 보존).
- 데이터: v4 dev (`C:\ct\external\carttrace_cdv_evaluation_v4`, zip sha256 `a1fbd502…`). episodes `e861435a32ff7a1c63a4309d1f290c941d5ecd61c25c6c5184c30708b244f80c`, transactions `580b2cdaceeb941b81b351004fb27d6e8e0fe450d3295ee540d81d2163febecb`, transaction_gold `af0f401877b07e9359518b55da18dc3051b2951b8110b279f48bccff0739b610`, episode_gold `1486013aeeabea1a4e85cb685a838ba4f1e0c48b2a7db624842e873e3a39af44`, matched_stockout `5e173215f4e0568fad010e08dc4d9ee8b17bac697b172f6be19df076323f1347`.
- 제외: 원본이 이미 본 여정인 2여정(노출 기록) → **430여정 / 1,474거래** + 매칭 96건. 봉인 표본 겹침 0.
- 입력 조건: (A) 쇼핑객·에이전트 턴만 추출기에. (B) source=seller tool 턴도 추출기에. tool 턴은 두 조건 모두 M1의 비사용자 문장, catalog listing_text는 A-VIP 라벨, 플랫폼 tool 턴 재고 0은 플랫폼 증거, checkout 수령 방식·기간·결제 총액(수수료 포함)은 결제 시점 사실.
- 비교군(같은 추출 공유): B0, B1(M1 Only), B2(M2 Only), B3(CDV-Wallet), B4(재확인 끔), **AV0(A-VIP 단독), AV1(A-VIP + 단순 조건), AV2(A-VIP + 누적 조건)**(정의 `docs/COMPARISON_ARMS_20261126.md` `ffe778d4c6fd735b6014144f6d7ef7a65b5907de82f127be93178b0db62aa750`), U 참고값(정답 조건, 따로 보고). B1·B3·B4의 M1은 M1 v2(주 M1 확정 전 dev 실행).
- 규칙·코드: `cdv/m1.py` `1a642a2121cce5b68f5adfe8d2491306da9d3ef7962088f945f5f83a970ce160`(c156160), `cdv/v2/scope.py` `3d34b595f85b0e6a72a93e691b6dd377da5af1aee53bd34a123a0fe8948b4b22`, `cdv/v2/integrate.py` `9d9894dc413810fe7efbba1066401e95e23644d0aacc9e814c233118062cb983`, `cdv/v2/m1v2.py` `4cccd520063bcf3a36b6a5df1f4de8717286e2102e6225de4f76a978bb18c6c6`, `eval/integrated/arms.py` `66a4a4fe298be3787ea8167e20b017150db0b33a415032f33f57e8825d63227d`, 실행기 `eval/extdata/run_ext.py` `3810a940fc9f4ed6745695361054e8c635d49e67dad27244c52207d2f691841c`, `cdv/extract.py` `444f55f948f3a7c3c8747abe03fb81bc807bba02ca6fa63c843eb7b0d69ce94b`.
- 모델: gpt-6-luna, PLAN_v3와 같은 설정. 원장 `results/extdata_20261126/ledger_v4.jsonl`(조건 B는 같은 요청이면 캐시 재사용).
- 호출 수: 드라이런 하한 (A) 1,397, (B) 1,397. 인자 생성 포함 추정 (A) 약 2,200, (B) 추가 약 700–900.
- 비용: 추정 약 $0.30–0.40, **상한 $0.60**(누적: A `--budget 0.35`, B `--budget 0.60`).
- 명령: `run_ext.py --data <v4> --name v4 --split dev --with-matched --budget 0.35` → `... --with-matched --seller-to-extractor --budget 0.60`.
- 무과금 후속 분석: (B)에서 추출기가 속은 사례 수((A) 대비 판매자 턴 이후 상태 변화), 매칭 뷰(쌍당 6건, reference_verdict, pair_similarity 층), 권한 축 분리. 오염 주입 조건(candidate_operations: M2 Only는 전부 반영, M1+M2는 v1·v2·M1-G가 수용한 것만 → follows_rejected_proposal 거래의 부당 허용률)은 `eval/v4check/contamination.py`로 따로 실행.
