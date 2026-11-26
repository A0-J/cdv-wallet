# 봉인 표본 실행기 고정 검사(허용 목록 방식) 시험 기록 — 2026-11-27, 모델 호출 0

- 대상: `eval/seal/run_sealed.py::check_frozen` (조정 24). 다른 코드는 바꾸지 않음.
- 판정 코드가 `paired_compare`를 불러 쓰는지: cdv/, eval/integrated/(파일 자신 제외), eval/e_m1/, eval/m1_v2/ 검색 결과 0건.
- 시험 결과:
  - 현재 저장소 → 통과
  - 네 폴더를 그대로 복사한 사본 → 통과
  - 사본에서 `cdv/verdict.py` 한 줄 추가 → 거부 (`changed: cdv/verdict.py`)
  - 사본에 `eval/integrated/extra.py` 추가 → 거부 (`added (not allow-listed): eval/integrated/extra.py`)
