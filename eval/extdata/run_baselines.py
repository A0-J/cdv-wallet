"""LLM baselines on the external synthetic data (v4 common format): PRECHECK and SUMMARY (cdv/v2/baselines.py).

Same transactions, exclusion and gate as eval/extdata/run_ext.py. Input to the models: shopper/agent turns only
(condition A). Gold files are used for scoring only.
  PRECHECK  one call per payment request (transactions + matched): allow / block / clarify -> ALLOW / DENY / CLARIFY
  SUMMARY   one summary call per episode + one plain-LLM extraction call on the summary -> mandate -> full M2 gate
Output: results/extdata_20261126/baselines_{name}_{split}.jsonl, summary_baselines_{name}_{split}.json
Usage: dry  .venv/Scripts/python.exe eval/extdata/run_baselines.py --data <v4> --name v4 --split dev --dry-run
       live ... --budget 0.40   (approved: prompts sha d9c696fe...)
Harness options added 2026-11-27 after the policy freeze (prompts and decision code unchanged; defaults = old behaviour):
  --precheck-only     skip SUMMARY
  --seller-in-input   condition B: seller tool turns enter the PRECHECK input as agent turns (same mapping as
                      run_ext.py --seller-to-extractor); without --run-tag it shares the condition-A ledger, so
                      identical requests (no seller turn) replay A's answers and only changed inputs are paid
  --run-tag T         separate output suffix AND separate ledger (no replay; used for the run-to-run agreement)
  --cap-new-spend X   cap on NEW spend of this run (budget = what the ledger already holds + X)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import arms as A  # noqa: E402
import run as R  # noqa: E402
import run_ext as X  # noqa: E402
from cdv import verdict  # noqa: E402
from cdv.extract import OpenAIResponses, PlainLLM, Turn  # noqa: E402
from cdv.v2 import baselines as Bl  # noqa: E402

OUT = ROOT / "results" / "extdata_20261126"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--name", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=0.40)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--precheck-only", action="store_true")
    ap.add_argument("--seller-in-input", action="store_true")
    ap.add_argument("--run-tag", default="")
    ap.add_argument("--cap-new-spend", type=float, default=None)
    a = ap.parse_args()
    d = a.data / a.split
    eps = {e["episode_id"]: e for e in X.jl(d / "episodes.jsonl")}
    tg = {g["transaction_id"]: g for g in X.jl(d / "transaction_gold.jsonl")}
    mg = {g["challenge_id"]: g for g in X.jl(d / "matched_stockout_gold.jsonl")}
    excl = set(json.loads((OUT / f"exclusion_{a.name}_{a.split}.json").read_text(encoding="utf-8"))["excluded_episodes"])
    txs = [("tx", t) for t in X.jl(d / "transactions.jsonl") if t["episode_id"] not in excl] + \
          [("matched", t) for t in X.jl(d / "matched_stockout.jsonl") if t["episode_id"] not in excl]
    keep = sorted({t["episode_id"] for _, t in txs})
    tag = (f"{a.name}_{a.split}" + ("_B" if a.seller_in_input else "") + (f"_{a.run_tag}" if a.run_tag else "")
           + ("_dry" if a.dry_run else ""))
    assert a.dry_run or not (OUT / f"baselines_{tag}.jsonl").exists(), "refusing to overwrite"
    ledger = OUT / f"ledger_baselines_{a.name}{('_' + a.run_tag) if a.run_tag else ''}.jsonl"
    budget = a.budget
    if a.cap_new_spend is not None:
        held = sum(json.loads(l).get("cost_usd", 0.0) for l in ledger.read_text(encoding="utf-8").splitlines() if l) if ledger.exists() else 0.0
        budget = held + a.cap_new_spend
    llm = R.DryLLM() if a.dry_run else OpenAIResponses("gpt-6-luna", ledger, budget)

    def turns(ep):
        out = []
        for t in ep["dialogue"]:
            if t["role"] in ("user", "assistant"):
                out.append(("shopper" if t["role"] == "user" else "agent", t["text"]))
            elif a.seller_in_input and t["role"] == "tool" and t.get("source") == "seller":
                out.append(("agent", t["text"]))       # condition B: as the extractor sees it in run_ext.py
        return out

    def pre_job(item):
        kind, tx = item
        ep = eps[tx["episode_id"]]
        cat = {c["sku"]: c for c in ep["catalog"]}
        lines = [{"title": cat.get(l["sku"], {}).get("title") or l["sku"], "brand": l.get("brand"), "unit_price": l["unit_minor"] / 100,
                  "quantity": l["quantity"]} for l in tx["checkout"]["lines"]]
        try:
            return Bl.precheck(llm, turns(ep), lines, fees=(tx["checkout"].get("fees_minor") or 0) / 100,
                               fulfillment=tx["checkout"].get("fulfillment"), days=tx["checkout"].get("days"))
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001
            return ("ERROR", True, 0.0, repr(e))

    def sum_job(e):
        try:
            text, c1 = Bl.summarize(llm, turns(eps[e]))
            pl = PlainLLM(llm).run([Turn("user", text, "s0")])
            return e, (text, pl["state"], c1 + pl["cost_usd"])
        except SystemExit:
            raise
        except Exception as ex:  # noqa: BLE001
            return e, ex
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        pre = list(ex.map(pre_job, txs))
        summ_ext = {} if a.precheck_only else dict(ex.map(sum_job, keep))
    if a.dry_run:
        out = {"precheck_calls": len(txs), "summary_episodes": len(keep), "calls_lower_bound": llm.calls,
               "input_tokens_est": int(llm.chars_in / 4), "prompts_sha256": Bl.PROMPTS_SHA256}
        (OUT / f"summary_baselines_{tag}.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(out))
        return
    rows, tab = [], defaultdict(Counter)
    for (kind, tx), p in zip(txs, pre):
        ep = eps[tx["episode_id"]]
        g = (tg.get(tx["transaction_id"]) if kind == "tx" else mg.get(tx["challenge_id"])) or {}
        se = summ_ext.get(tx["episode_id"])
        sdec = None if a.precheck_only else "ERROR"
        if se is not None and not isinstance(se, Exception):
            case = X.build_case(ep, tx, g)
            env = A.Env(case)
            m = A.ledger_to_mandate(A.raw_ctx([{"seq": 0, "state": se[1]}]), case.reg, case.seller, f"m-{case.episode_id}", 1, env.session)
            d_, c_ = env.full_gate(m)
            sdec = verdict.integrated(d_, c_, False)
        key = (kind, g.get("transaction_type") or g.get("intent_case"), g.get("expected_checkout") or g.get("reference_verdict"))
        tab[("PRECHECK",) + key][p[0]] += 1
        if not a.precheck_only:
            tab[("SUMMARY",) + key][sdec] += 1
        rows.append({"kind": kind, "id": tx.get("transaction_id") or tx.get("challenge_id"), "episode_id": tx["episode_id"],
                     "type": key[1], "expected": key[2], "precheck": p[0], "precheck_unparsed": p[1], "summary": sdec,
                     "follows_rejected_proposal": g.get("follows_rejected_proposal")})
    (OUT / f"baselines_{tag}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n")
    out = {"prompts_sha256": Bl.PROMPTS_SHA256, "input_condition": "B (seller turns in input)" if a.seller_in_input else "A",
           "precheck_only": a.precheck_only, "ledger": ledger.name, "rows": len(rows),
           "cost_usd_ledger_total": round(llm.spent, 6), "cache_hits": llm.cache_hits,
           "summary_failures": sum(1 for v in summ_ext.values() if isinstance(v, Exception)),
           "precheck_unparsed": sum(1 for p in pre if p[1]),
           "table": {"|".join(map(str, k)): dict(v) for k, v in sorted(tab.items(), key=lambda kv: str(kv[0]))}}
    (OUT / f"summary_baselines_{tag}.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in out.items() if k != "table"}))


if __name__ == "__main__":
    main()
