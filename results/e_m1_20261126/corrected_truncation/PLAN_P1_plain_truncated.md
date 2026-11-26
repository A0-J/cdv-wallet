# P1 계획: 일반 LLM 비교군의 결제 요청 시점 절단 재추출 (test_cross_store, 사후 교정)

- 작성: 2026-11-26. 연구자 승인 범위: "일반 LLM 구성의 절단 대화 재추출(R1·R3·R2)".
- 목적: PLAN_v3 일반 LLM 팔은 결제 요청 뒤 발화까지 한 번에 읽었다. FnCTOD 세 팔처럼 판정 시점 t 이전 대화로 다시 추출해 교정 표를 완성한다. **사후 측정 교정이며 설계·규칙 결정에 쓰지 않는다.**
- 데이터: PLAN_v3 R1 200 / R3 100 / R2 96여정(test_cross_store; R2는 네 분할에서 뽑음 → 네 분할 모두 읽고 하나라도 없으면 멈춤).
- 입력: t 이전 쇼핑객·에이전트 메시지(공용 정의 `recompute_truncated.decision_point`). 숨은 사양은 입력이 아니다.
- 모델: gpt-6-luna, Responses API, reasoning low, max_output_tokens 2000 (PLAN_v3와 같음). 프롬프트 코드 `cdv/extract.py::PlainLLM` 그대로.
- 판정: `cdv.verdict.plan_v3(None, cart_check(...))` (PLAN_v3와 같은 함수).
- 호출 수: **396** (여정당 1회, 드라이런 확인). 대화 문자 868,699.
- 비용: 추정 약 $0.06 (PLAN_v3 원장 기준 일반 LLM 호출당 약 $0.0001–0.00016). **상한 $0.12** (`--budget 0.12`, 초과 시 OpenAIResponses가 멈춤).
- 출력(새 파일): `corrected_truncation/plain_{R1,R3,R2}_test_cross_store.jsonl`, `plain_summary.json`, 원장 `ledger_plain_truncated.jsonl`. 덮어쓰기 거부.
- 보고: 원(누설) 대 교정, 정상/위반 × ALLOW/CLARIFY/DENY, 바뀐 여정 수, 호출 수, 비용.
- 코드 sha256
  - eval/e_m1/plain_truncated.py `f5c53fbc87c346887175f5e32389df5dceb854203aadd97f818f4485b88c285e`
  - eval/e_m1/recompute_truncated.py `b0f04b99c5a3171296ad3080c809e8012d9100056a78d26270d1632dc6dc8ee6`
  - cdv/extract.py `444f55f948f3a7c3c8747abe03fb81bc807bba02ca6fa63c843eb7b0d69ce94b`
  - cdv/verdict.py `91c1e0403353122fdbeae8b609b6a118fa678fd79f777d84b773aadad0661fe0`
  - cdv/pipeline.py `3939dc957fd9770b76aa23bee94df9cb17d96ea663f63cd3e0c7b5fcf06967db`
- 실행 명령: `.venv/Scripts/python.exe eval/e_m1/plain_truncated.py --budget 0.12`
