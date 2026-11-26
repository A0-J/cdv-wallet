"""Check before using the runner change (m1g_memo.py) on v4b: on v4 dev, sequential run_arms vs (parallel prewarm +
in-run reuse) give identical decisions for every configuration. No model calls: both modes use the SAME ledger-only
replay client (answers fixed), so only the runner logic is compared. Transactions whose requests are not all in the
ledger are counted and left out (never sent).
Usage: .venv/Scripts/python.exe eval/review/memo_equivalence.py [condition A|B]
Output: results/review_20261127/MEMO_EQUIVALENCE_<cond>.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata", "eval/review"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import arms as A  # noqa: E402
import run_ext as RX  # noqa: E402
from cdv.v2.m1g_path import run_m1g_path  # noqa: E402
from m1g_memo import MemoLLM, prewarm  # noqa: E402
from replay import Replay  # noqa: E402

X = ROOT / "results" / "extdata_20261126"
V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4/dev")


def jl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def main(cond="A"):
    src = X / ("rows_v4_dev_A.jsonl" if cond == "A" else "rows_v4_dev_B.jsonl")   # same extraction as R-v4g (cached)
    rows = jl(src)
    eps = {e["episode_id"]: e for e in jl(V4 / "episodes.jsonl")}
    txs = {t["transaction_id"]: t for t in jl(V4 / "transactions.jsonl")}
    tg = {g["transaction_id"]: g for g in jl(V4 / "transaction_gold.jsonl")}
    from cdv.nli import NLI
    nli = NLI()
    cases = {r["transaction_id"]: RX.build_case(eps[r["episode_id"]], txs[r["transaction_id"]], tg.get(r["transaction_id"]) or {}) for r in rows}

    def st_of(r, case):
        return sorted([{"seq": int(s["turn_id"][1:]), "state": s["state"]} for s in r["fnctod_states"] if int(s["turn_id"][1:]) < case.t],
                      key=lambda s: s["seq"])

    def brands(st):
        return sorted({str(b) for s in st for k in ("brand_include", "brand_exclude") for b in ((s["state"].get(A.PC) or {}).get(k) or [])})
    seq_llm = Replay(X / "ledger_m1g_v4.jsonl")
    par_llm = MemoLLM(Replay(X / "ledger_m1g_v4.jsonl"))
    jobs = []
    for r in rows:
        c = cases[r["transaction_id"]]
        st = st_of(r, c)
        jobs.append(lambda c=c, st=st: run_m1g_path(st, c.user_turns, c.agent_turns, c.reg, c.t, par_llm, known_brands=brands(st)))
    pre_err = prewarm(jobs, par_llm)
    same = diff = skipped = 0
    diffs = []
    for r in rows:
        c = cases[r["transaction_id"]]
        states = [{"turn_id": s["turn_id"], "state": s["state"]} for s in r["fnctod_states"]]
        m0 = seq_llm.misses
        try:
            o_seq = A.run_arms(c, states, nli=nli, gold=None, m1_llm=seq_llm)
            o_par = A.run_arms(c, states, nli=nli, gold=None, m1_llm=par_llm)
        except RuntimeError:
            skipped += 1
            continue
        if seq_llm.misses > m0:
            skipped += 1
            continue
        for arm in o_seq["arms"]:
            if o_seq["arms"][arm]["decision"] == o_par["arms"][arm]["decision"] and o_seq["arms"][arm].get("codes") == o_par["arms"][arm].get("codes"):
                same += 1
            else:
                diff += 1
                diffs.append((r["transaction_id"], arm, o_seq["arms"][arm]["decision"], o_par["arms"][arm]["decision"]))
    md = [f"# 실행기 변경 확인: 순차 대 병렬(사전 호출 + 실행 안 재사용), v4 dev 조건 {cond}, 모델 호출 0", "",
          f"- 거래 {len(rows)}, 비교한 거래 {len(rows) - skipped}, 원장에 없는 요청 때문에 뺀 거래 {skipped}(보내지 않음), 사전 호출 오류 {pre_err}.",
          f"- 비교군×거래 판정(사유 코드 포함) 같음 {same}, 다름 **{diff}**.",
          f"- 병렬 방식의 요청 수(재사용 전) {par_llm.requested}, 서로 다른 요청 {par_llm.distinct}."]
    md += [f"  - 다름: {d}" for d in diffs[:20]]
    out = ROOT / "results" / "review_20261127" / f"MEMO_EQUIVALENCE_{cond}.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "A")
