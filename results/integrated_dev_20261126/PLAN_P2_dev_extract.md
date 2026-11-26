# P2 계획: validation 개발용 추출 (M1 v2·통합 평가 개발)

- 작성: 2026-11-26. 연구자 승인 범위: "validation 개발 추출".
- 목적: M1 v2와 통합 파이프라인의 개발(문턱·정책 결정, 안 B 기준 측정)을 이미 본 test가 아닌 validation에서 한다.
- 데이터(validation만, 시드 20261127, PLAN_v3 선택 규칙 재사용):
  - V1 R1형 200 (드라이런: RIGHT 146, RIGHT_BY_LUCK 8, WRONG 36, WRONG_HIDDEN 10)
  - V3 R3형(품절) 100 (RIGHT 80, WRONG 17, WRONG_HIDDEN 3)
  - V2 R2형(고르기 뒤 거절) — validation에는 **6여정뿐**(RIGHT 1, WRONG 5). 그대로 포함하고 수가 작음을 보고한다.
- 입력: 판정 시점 t 이전 쇼핑객·에이전트 메시지만(누설 차단). 추출은 FnCTOD(턴마다 선택 + 인자) + 일반 LLM 1회.
- 모델: gpt-6-luna, PLAN_v3와 같은 설정과 코드(`cdv/extract.py`).
- 호출 수: 드라이런 하한 **1,081**(V1 654, V3 367, V2 60; 드라이 응답은 함수를 고르지 않아 인자 생성 호출이 빠짐). 실제 추정 약 1,800–2,200.
- 비용: 추정 약 $0.20–0.25(PLAN_v3 실측 여정당 R1형 $0.0007, R3형 $0.0008, 절단으로 더 적음). **상한 $0.40**(세트별 `--budget` 합).
- 출력(새 폴더): `results/integrated_dev_20261126/extract_{V1,V3,V2}.jsonl`, 요약, 원장 `ledger.jsonl`. 덮어쓰기 거부.
- 평가는 별도 무과금 단계(`eval/integrated/arms.py`, B0–B4 + U 참고). 이 추출로 정하는 것: M1 v2 문턱, 안 B 기준 측정, 추출기가 속는 비율(T3 생성 사례는 P3·통합 단계에서).
- 코드 sha256
  - eval/integrated/extract_dev.py `7fff05f38ecf44b44274a8eba6043eafa454e1a7b8442c89940dc276e53f3e2f`
  - eval/e_m1/run.py `7557288acbd4314b7923b5be1fd6cb6914ee744e63aa67957571878b35a26b04`
  - eval/e_m1/recompute_truncated.py `b0f04b99c5a3171296ad3080c809e8012d9100056a78d26270d1632dc6dc8ee6`
  - cdv/extract.py `444f55f948f3a7c3c8747abe03fb81bc807bba02ca6fa63c843eb7b0d69ce94b`
- 실행 명령: `extract_dev.py --set V1 --n 200 --budget 0.25`, `--set V3 --n 100 --budget 0.12`, `--set V2 --n 100 --budget 0.03`
