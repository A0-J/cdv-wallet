# E-M1 실행 기록

## 승인

- 2026-11-26 연구자 지시: "현재 PLAN_v3를 기준으로 구현 및 평가 조건을 고정하고 E-M1 본실험을 우선 진행"
- 승인된 계획: `PLAN_v3.md` sha256 `2ccee2f06fddfa23b86cea39a9d590adfe196b124f8b881b0a4f7556814b8acf` (실행 직전 재확인 일치), 상한 $15
- 추가 지시: 검증 규칙은 validation에서 고친 상태로 고정, test 결과를 보고 고치지 않는다. 추가 기능·범위 확장 보류.

## 모델 확인 (무과금)

- `GET /v1/models` HTTP 200, 모델 103개. `gpt-6-luna` 있음(계획 모델).
- 키: 연구자가 지정한 파일(`C:\agentic-wallet-security\openai_api_key.txt`, 공개 repo에서 `.gitignore`로 제외·추적 안 됨)의 값을 실행 셸의 `OPENAI_API_KEY` 환경 변수로만 넘긴다. 코드는 환경 변수만 읽는다. 키는 출력·기록하지 않는다.

## 실행 전 하네스 변경 (평가 조건 변경 없음)

PLAN_v3 9절 고정 이후 아래 두 파일을 바꿨다. 비교군, 데이터 선택, 지표, 모델, 프롬프트, 검증 규칙(m1.py, pipeline.py, nli.py)은 그대로다.

| 파일 | 변경 | 이유 | 새 sha256 |
|---|---|---|---|
| cdv/extract.py | 일시 오류(429, 5xx, 네트워크) 재시도 최대 5회와 기록. 이미 완료된 같은 요청(요청 sha256 같음)은 ledger의 응답을 재사용(재과금 없음). 스레드 잠금 | 한 번의 429로 전체가 멈추는 것 방지, 중단 뒤 재실행 시 중복 과금 방지, 병렬 실행 | 90a71cc969a5bd5d55a78926af5edf1936f390c8421788ce232c5105fd44c726 |
| eval/e_m1/run.py | 추출(API)을 여정 단위로 병렬(`--workers`, 기본 8), 검증은 순차. 행 파일에 FnCTOD 턴별 상태, 일반 LLM 상태, M1 추적을 저장. 실패 여정은 버리지 않고 `failed_journeys`로 보고 | 실행 시간, 대표 사례 정리, 실패 은폐 방지 | 7557288acbd4314b7923b5be1fd6cb6914ee744e63aa67957571878b35a26b04 |

- 프롬프트를 만드는 코드(FnCTOD, PlainLLM 클래스 본문)는 바꾸지 않았다.
- 점검 중 무과금 dry-run 요약 파일 두 개를 덮어썼다: `summary_R1_validation_dry.json`(10여정), `summary_G1_eval_dry.json`(20건). 네트워크 없는 비용 추정 파일이다.

## 실행 순서

파일럿(validation 10) → R1 → R3 → R2 → G1. 각 단계의 비용·실패 수를 아래에 덧붙인다.

## 파일럿 (validation R1 10여정, gpt-6-luna)

- 1차: 호출 51회, $0.0058, 오류 0. **파싱 문제 두 가지 발견:**
  - 함수 선택 출력 26개 중 7개(27%)가 `<domain>` 대신 `<shopping>set_purchase_conditions</shopping>` 형식 → 선택 없음으로 처리됨
  - 일반 LLM이 스키마 밖 값을 냄(수령 "regular delivery"/"express", 수량 "one of each", 품목 종류 목록)
- 1차 결과는 지우지 않고 `rows/summary_R1_validation_pilot_parse1.*`로 이름만 바꿔 두었다.
- **출력 파싱만 고쳤다(PLAN_v3 6절 허용 범위):** 선택 태그는 같은 이름의 태그 쌍이면 받음, `normalize_args`로 값 정규화(수령 방식 동의어, 숫자 단어, "one of each"→필수 품목 수, 금액 문자열, 목록→문자열). 모든 추출기에 똑같이 적용. 검증 규칙(m1.py, pipeline.py, nli.py)은 그대로.
- 2차(같은 10여정): 캐시 재사용 47회, 누적 비용 $0.0074, 실패 0. 선택 누락 해소.
- 파일럿 값은 본 지표에 넣지 않는다. 검증 규칙은 파일럿을 보고 바꾸지 않았다.
- 고친 뒤 해시: cdv/extract.py `444f55f948f3a7c3c8747abe03fb81bc807bba02ca6fa63c843eb7b0d69ce94b`, eval/e_m1/run.py `7557288acbd4314b7923b5be1fd6cb6914ee744e63aa67957571878b35a26b04`

## 본 실행

- 시작: 2026-11-26 13:57, 순서 R1(test_cross_store 200) → R3(100) → R2(96) → G1(260), workers 8, 누적 상한 $15
- 종료: 2026-11-26 14:44. R1 13:57–14:10, R3 14:10–14:16, R2 14:16–14:34, G1 14:34–14:44
- 누적(파일럿 포함): 호출 4,752회, 오류 0, 재시도 0, 비용 $0.6053. 실패 여정 0(R1 200, R3 100, R2 96, G1 260)
- 분석: `eval/e_m1/analyze.py` → `analysis/`. 결과 보고: `RESULTS.md`
