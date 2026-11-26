# 고정 뒤 dev 실행 계획 (정책 고정 커밋 610a97c)

- 모든 실행은 커밋 **610a97c**의 코드로 한다. 고정 뒤에는 어떤 결과를 봐도 규칙·정책을 고치지 않는다.
- 코드 sha256(커밋 기준): `cdv/v2/m1g.py` `3062ec1355ccbd2def0bc73f858713f3c559a181d21ba63a26b2e158fc463c83` (ACTIVE_VERSION v2, 프롬프트 sha `36b3ce71…`), `cdv/v2/m1g_path.py` `cba0508dd8cb173212c03a8c2cb058710e6e0ff94f269d20f45a8547c6647821`, `eval/integrated/arms.py` `fd1641c20ba122b27f9871ca64ff8b2ccb22b4de8acb4483559566dfb6c634fc`, `eval/integrated/dev_eval.py` `90104e16aab122d809cbf4a993e2467965312a0eabc2bc35bfbb3e7c59f49264`, `eval/extdata/run_ext.py` `4fb214f028b4c6566c62e6a12a46e10e6c7d86d5a8bd9b2cc09cd39dcff19e1a`, `eval/extdata/run_baselines.py` `f4b05190212d0f1a0ac8afee630e38bfbf96bd6e8e39c55b0f78787caaaafe79`, `cdv/v2/baselines.py` `09e35449a6e481f766faa18591a4fa5e3d7ef1fd451ba8cdc22560f85335b1d6` (프롬프트 sha `d9c696fe…`), `cdv/m1.py` `1a642a2121cce5b68f5adfe8d2491306da9d3ef7962088f945f5f83a970ce160`.

| 실행 | 데이터 | 명령 | 호출(추정) | 상한 | 승인 |
|---|---|---|---:|---:|---|
| R-val | validation 306여정 (P2 추출 재사용) | `dev_eval.py --m1g --tag frozen_m1g --m1g-budget 0.10` | M1-G 882 | $0.10 | 2026-11-26 결정 4 |
| R-base | v4 dev 430여정 / 1,474거래 + 매칭 96 | `run_baselines.py --data <v4> --name v4 --split dev --budget 0.40` | 2,430 | $0.40 | 2026-11-26 결정 3 |
| R-v4g | v4 dev (A) (P4 추출 캐시 재사용) | `run_ext.py --data <v4> --name v4 --split dev --with-matched --m1g --tag m1g --budget 0.60 --m1g-budget 0.20` | M1-G 약 1,100 | $0.20 | 2026-11-26 결정 4 |

- R-v4g는 P4 (B)가 원장 기록을 끝낸 뒤 시작한다(같은 원장 동시 기록 방지). 추출 캐시가 안 맞는 요청이 있으면 그만큼 추출 비용이 나며, 전체 상한($5) 안에서 처리하고 기록한다.
- 보고: validation B3 대 B4(M1-G 기준), B2 대 B3, B3 대 B3_v2(규칙), 미검증 정책 반영 결과. v4 dev: 비교군 전체(B0–B4, B3_v2, AV0–AV2, 두 기준선), 입력 조건 (A)·(B), 매칭 6유형, E2 발동(거짓 전제 동의).
