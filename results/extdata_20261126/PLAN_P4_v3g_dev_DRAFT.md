# P4 계획 초안: 외부 합성 데이터 통합 실행 (v3g dev) — 판 선택 대기

- 작성: 2026-11-26. **상태: 초안.** 연구자가 유료 실행에 쓸 판(v3g 또는 v3c)을 정한 뒤 최종판을 만들고 sha256을 다시 보고한다.
- 목적: 같은 합성 거래에서 B0–B4(+ U 참고값)를 비교한다. v3g dev는 형식·실행 점검용이다(v3g README). 주 결과는 연구자가 정한 판의 eval이다.
- 데이터: v3g dev(폴더 20:24 판). 파일 sha256: episodes `b68792c2ccd2336f2bde29cbd9f7e9350d758f686c01077e381b490e28278945`, transactions `e94012d8897a45d93983ff022d6e0eeac745a0c5e8301f2f4e8a834f6782510d`, transaction_gold `03006ecaed240d8b2a83476baf441d07651aed4f2a102625ecf8fdd09ff94825`, episode_gold `af8167ffe72b63cc997e739ca8ee5fb0abd6984de2fb5a53cf500b2579972cb4`.
- 제외(실행 전 확정): 원본 여정이 이미 본 여정인 2여정(노출 기록) → **398여정 / 723거래**. 봉인 표본과 겹침 0. 목록 `exclusion_v3g_dev.json`.
- 입력: 대화의 user/assistant 턴만 추출기에. tool 턴(판매자·플랫폼 글)은 M1의 비사용자 문장과 A-VIP 라벨로만. checkout.fulfillment / days는 결제 동의 시점 사실. 정답 파일은 채점에만.
- 모델: gpt-6-luna, PLAN_v3와 같은 추출 코드(`cdv/extract.py` `444f55f948f3a7c3c8747abe03fb81bc807bba02ca6fa63c843eb7b0d69ce94b`). 여정당 추출 1회를 다섯 비교군이 공유.
- 호출 수: 드라이런 하한 1,867(선택 1,469 + 일반 398), 인자 생성 포함 추정 약 3,000. 비용 추정 약 $0.30–0.35, **상한 $0.60**.
- 규칙: 금액 명세 MONEY-1을 반영한 `cdv/m1.py` `5392c32753fb45416075f7bab13b164984fdfc3a7d58db0341301cd97cf85efc`, M1 v2 `cdv/v2/`, 비교군 `eval/integrated/arms.py` `1a8eb291bd43decb4a5be678172a781b2b1f5a3f883dcf6dda6cb1a3449fdab3`, 실행기 `eval/extdata/run_ext.py` `800d167822d40210ab57fff7384f5fc3748bc304baa5e498dfab74248dd342a4`.
- 채점: transaction_gold.expected_checkout(allow / block) 대 비교군 판정(ALLOW / CLARIFY / DENY). 권한(grant) 축과 매칭 품절 뷰는 따로 보고하고 주 결과에 합치지 않는다.
- 무과금 연결 시험(빈 추출, 60거래): 오류 0. U 참고값은 allow 24 중 23 허용, block 36 중 31 차단.
