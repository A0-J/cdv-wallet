# 계획 v3: E-M1 — FnCTOD 추출 + M1 검증 (유료, 승인 요청용)

- 작성: 2026-11-26
- **이 판이 `PLAN_v2.md`(sha256 `f95bf00edaea895c7f19dfa7893668410de52d3271a4c6e4a86bb5df3578cad8`, 미승인)를 대체한다.** v2는 지우지 않았다.
- 비교군, 데이터, 지표, 가설, 모델, 비용, 절차는 **v2 1~8절과 같다.** 아래 0절의 변경과 9절의 코드 고정만 더했다.
- **상태: 승인 대기. 유료 호출은 0회다.**

## 0. v2에서 바뀐 것 (코드만, 계획 내용은 그대로)

실제 사례 하나(CartTrace validation `ep-b63223f61e0a`)로 전체 동작을 돌리다가 아래를 찾아 고쳤다. 모두 validation 사례에서 찾았고, 시험 분할을 보고 고친 것은 없다.

1. **M1 규칙: 매장 수령 표현.** "collect it in store"를 매장 수령으로 인식하지 못했다. `PICKUP_RE`에 `collect (it|them) (in|at|from) (the) store`를 더했다.
2. **M1 규칙: 조건부 대체 오인.** "If it is out of stock, just tell me"를 조건부 대체 허용으로 읽었다(실제로는 반대 뜻). `CONDITIONAL_RE` 뒤에 "tell me / let me know / ask me / check with me / don't substitute" 부정 미리보기를 더했다.
3. **파이프라인: 대기 항목이 사라지는 문제.** 앞 턴에서 PENDING(사용자 확인 대기)이 된 항목이, 뒤 턴에 근거 없는 값이 다시 제안되어 REJECT되면 대기 목록에서 빠졌다. 그러면 확인 없이 조용히 누락된다. 이제 같은 항목에 대한 뒤 턴의 ACCEPT 또는 PENDING만 앞의 대기를 대신한다.
4. **하네스:** 실제 실행 결과 파일(`rows_*.jsonl`)을 덮어쓰지 않도록 막았다.
5. 회귀 시험 3개를 더했다. 전체 57개 통과.

변경 1~2를 반영한 누락 검사 재실행(무과금, 새 파일, 이전 결과는 그대로 둠):

| 분할 | 지표 | 이전 | 수정 뒤 |
|---|---|---:|---:|
| test_cross_store | 수령 방식 탐지율 | 60.5% | 64.5% |
| test_cross_store | 조건부 대체 오경보율 | 1.08% | 0.47% |
| validation | 수령 방식 탐지율 | 59.3% | 64.8% |
| validation | 조건부 대체 오경보율 | 0.86% | 0.45% |

나머지 항목의 값은 바뀌지 않았다. 파일: `results/omission_realtext_20261126/summary_*_v3_rulefix.json`

## 9. 코드 고정 (본 실행은 아래 해시의 코드로만 한다)

| 파일 | sha256 |
|---|---|
| cdv/canon.py | 33a077b152f5ad2ee6d152c0d9343a2c55c120947c1e201b47c3becf098d4b4f |
| cdv/mandate.py | c19dcdfeb054b41246e6b83d702ffbe8969ad7879d62c21434a0a051fa05662a |
| cdv/evidence.py | 2c9614989b9ece275e55f390e83bd41fd5c7325c1704cb9e5ca00961449b5dc5 |
| cdv/gate.py | a4d82eacf06d7f731c3041a3589103350414cfb2fab139757ef77466a5bd95c8 |
| cdv/m1.py | 66910faa9887f21601ea1e4491efe42e4c320a4b2d5ec92e87612ceadef1ac54 |
| cdv/extract.py | 5e47a738b043ec67d9b0de63f955029f88d68e6785f489c08a0daa24d08181d6 |
| cdv/pipeline.py | 3939dc957fd9770b76aa23bee94df9cb17d96ea663f63cd3e0c7b5fcf06967db |
| cdv/nli.py | 95d9f1e368df57eaa8f736230dff5a66836d18f575a5b6be6491c4e21da8475f |
| eval/e_m1/run.py | 271a33ac9a72fdd74f801dfdda5890e5776542edd88df498f0140a8409a0d362 |
| adapters/avip.py | f6e1210e2a3a7d81d70e4cc10294745fc6343e16cf1702a491904d85977be50c |

- 파일럿(10여정) 뒤 바꿀 수 있는 것은 v2 6절대로 **출력 파싱뿐**이다. 바꾸면 해시를 다시 적고 보고한다.
- 본 실행 시작 직전에 위 해시를 다시 확인해 `ledger.jsonl` 첫 줄에 적는다.
