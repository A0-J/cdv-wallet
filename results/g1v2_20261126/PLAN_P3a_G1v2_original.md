# P3a 계획: G1v2 원 문구판 추출과 평가 (PLAN_v3 고정 규칙)

- 작성: 2026-11-26. 연구자 결정: 심사 전에는 원 문구판만(바꿔 쓰기·T3·봉인 표본은 심사 뒤), 유형 N0·L1·L2·P1·S1·S2·U2, 추출 상한 $0.40, 평가 분할에는 PLAN_v3 고정 규칙 네 구성만.
- **이 계획은 생성 코드와 사례 파일 해시를 보고하기 위한 것이다. 추출(유료)은 연구자 확인 뒤 실행한다.**

## 데이터 (생성, 원본과 분리 보고)
- 생성기: `eval/templates/g1v2_make.py` (sha256 `c92dd99f88d9eb20b228d40c69ba6d45d74e186a4b80cd7a419e20d9cf0f1e6b`), 시드 20261128, 모델 호출 0.
- 문구 표(에이전트·쇼핑객 템플릿, 합성 상품명) sha256 `95a6d81c3761f34f6c539a2b67ae393e344eb4b7a486f51986a90c850281fd72`. WhisperBench·CartTrace 상품명 문구를 쓰지 않음(첫 쇼핑객 발화만 CartTrace 원문).
- 기반 여정: 첫 발화가 규칙으로 읽히는 예산을 직접 말하는 정상 여정, 첫 발화 문장 기준 중복 제거, 비복원 추출, 노출 기록 174여정 제외, P1은 묶음이 아닌 여정만. 분할 사이 기반 여정 겹침 0, 중복 대화 0(생성 중 검사).
- 개발(validation 기반) 140사례, 평가(test_cross_template 기반) 140사례, 유형당 20.
  - dev.jsonl sha256 `b83f585d7be5431034bb19aab1a124055778b2a21c6cf4822ba42193c8097ef5`
  - eval.jsonl sha256 `1115a4399f6be13755dfdf9bcdeaa526954a0a1dec21f3d758c7b743289efcd4`
  - manifest `results/g1v2_20261126/manifest.json` sha256 `774e925b3fb780b26a8e3c48bc2d330c54ce671c23fe8f7ce19548fb326baa8e`
- 정답(구성상): 최종 예산(P1은 수량 2 포함), 사용자 턴별 예산, '확인이 필요 없는 사례' 표시(N0·L1·L2·P1·S1).

## 추출
- 모델: gpt-6-luna, PLAN_v3와 같은 설정·코드(`cdv/extract.py` sha256 `444f55f948f3a7c3c8747abe03fb81bc807bba02ca6fa63c843eb7b0d69ce94b`). 사례마다 FnCTOD(턴마다 선택 + 인자) + 일반 LLM 1회.
- 호출 수: 드라이런 하한 분할당 490(선택 350 + 일반 140), 인자 생성 포함 추정 분할당 약 840, 합계 약 1,700.
- 비용: 추정 약 $0.20–0.25. **상한 $0.40**(같은 원장 누적: dev `--budget 0.20`, eval `--budget 0.40`).

## 평가 (무과금)
- 실행기: `eval/g1v2/run_g1v2.py` (sha256 `5e39992a79e579646d52e9b0c5de8b3642c004706356fa0ba1d14ff35131e15a`). 사례 파일 해시가 manifest와 다르면 멈춤.
- 비교군: plain, fnctod, fnctod_r, fnctod_rn. 규칙은 PLAN_v3 고정(`cdv/pipeline.py` `3939dc957fd9770b76aa23bee94df9cb17d96ea663f63cd3e0c7b5fcf06967db`, `cdv/m1.py` `66910faa9887f21601ea1e4491efe42e4c320a4b2d5ec92e87612ceadef1ac54`, `cdv/nli.py` `95d9f1e368df57eaa8f736230dff5a66836d18f575a5b6be6491c4e21da8475f`).
- 지표: 최종 정답(정당한 변경 반영 L1·L2·P1, 보존 N0·S1·S2·U2), 턴별 정답(L2 다중 변경), 다른 조건 보존(P1 수량), 확인 요청과 불필요한 확인 요청. 유형별로 보고하고, 추출기가 처음부터 맞힌 사례도 모두 포함한다.
- 개발 분할 결과는 M1 v2 개발용으로 쓸 수 있다. 평가 분할에는 위 네 구성만 돌린다.
