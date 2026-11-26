# PRECHECK 추가 측정 2건 (v4 dev, 고정 커밋 610a97c 이후) — 승인 2026-11-27

- 승인: 조건 (B) 상한 $0.15, 같은 입력 재실행(일치율) 상한 $0.25.
- 프롬프트·판정 코드 변경 없음: `cdv/v2/baselines.py` sha256 `09e35449a6e481f766faa18591a4fa5e3d7ef1fd451ba8cdc22560f85335b1d6` (프롬프트 sha `d9c696fe…`, 고정 커밋과 같음).
- 하네스 변경(옵션 추가, 기본 동작 그대로): `eval/extdata/run_baselines.py` 고정 시점 sha256 `f4b05190212d0f1a0ac8afee630e38bfbf96bd6e8e39c55b0f78787caaaafe79` → 변경 후 `3c63903be5206c0d83ead71de2943c20686b42fa0222bf41f7eb0f288f83e145`.
  - `--precheck-only`, `--seller-in-input`(판매자 tool 턴을 에이전트 턴으로 넣음, run_ext.py 조건 B와 같은 대응), `--run-tag`(별도 원장 = 재사용 없음), `--cap-new-spend`(이번 실행의 새 지출 상한).

| 실행 | 명령 | 호출 | 추정 비용 | 상한 |
|---|---|---:|---:|---:|
| PB (조건 B) | `run_baselines.py --data <v4> --name v4 --split dev --precheck-only --seller-in-input --cap-new-spend 0.15` | 판매자 글이 있는 여정의 거래 574 + 매칭 80 = 654 새 호출(나머지 916은 입력이 A와 같아 원장 재사용) | 약 $0.06 | $0.15 |
| PR (재실행) | `run_baselines.py --data <v4> --name v4 --split dev --precheck-only --run-tag run2 --budget 0.25` | 1,570 (새 원장, 재사용 없음) | 약 $0.13 | $0.25 |

- 근거: 조건 A PRECHECK 실측 1,570호출 $0.1304, 입력 647,964토큰, 출력 131,225토큰, 지연 중앙값 1.88초. 드라이런 입력 추정 A 629,865 / B 642,218토큰.
- 출력(덮어쓰기 거부): `baselines_v4_dev_B.jsonl`, `summary_baselines_v4_dev_B.json`, `baselines_v4_dev_run2.jsonl`, `summary_baselines_v4_dev_run2.json`, 원장 `ledger_baselines_v4.jsonl`(B 추가분), `ledger_baselines_v4_run2.jsonl`.
