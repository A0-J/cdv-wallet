"""P1: plain-LLM arm re-extracted on the dialogue cut at the decision point t (PLAN_v3 leak correction).

Same model, prompt code (cdv/extract.py::PlainLLM, unchanged) and decision rule (cdv/verdict.py::plan_v3)
as PLAN_v3; the only change is the input: shopper/agent messages with seq < t (shared definition
eval/e_m1/recompute_truncated.py::decision_point). One call per journey.
Reads all four splits; stops if any journey, dialogue or cart is missing.
Output (new files; PLAN_v3 files untouched): results/e_m1_20261126/corrected_truncation/plain_{set}.jsonl,
plain_summary.json; calls logged to results/e_m1_20261126/ledger_plain_truncated.jsonl.
Usage:
  dry:  .venv/Scripts/python.exe eval/e_m1/plain_truncated.py --dry-run
  live: .venv/Scripts/python.exe eval/e_m1/plain_truncated.py --budget 0.10   (after plan approval)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "e_m1"))
sys.path.insert(0, str(ROOT / "eval" / "m1_v2"))
import run as R  # noqa: E402
from cdv import verdict  # noqa: E402
from cdv.extract import OpenAIResponses, PlainLLM, Turn  # noqa: E402
from cdv.m1 import Ledger  # noqa: E402
from cdv.pipeline import cart_check, state_to_entries  # noqa: E402
from recompute_truncated import decision_point  # noqa: E402
import diagnose as D  # noqa: E402

RES = ROOT / "results" / "e_m1_20261126"
OUT = RES / "corrected_truncation"
SETS = ["R1_test_cross_store", "R3_test_cross_store", "R2_test_cross_store"]
SPLITS = ("train", "validation", "test_cross_store", "test_cross_template")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default="gpt-6-luna")
    ap.add_argument("--budget", type=float, default=0.10)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    rows = {s: [json.loads(l) for l in (RES / f"rows_{s}.jsonl").read_text(encoding="utf-8").splitlines() if l] for s in SETS}
    eids = {r["episode_id"] for rs in rows.values() for r in rs}
    T = D.load_turns(eids, splits=SPLITS)
    for m in D.load_msgs(eids, splits=SPLITS):
        D._CART[m["episode_id"]] = m["final_cart"]
    miss = sorted(e for e in eids if not T.get(e) or not D.load_cart(e))
    if miss:
        raise SystemExit(f"missing dialogue/cart for {len(miss)} journeys: {miss[:5]}")
    items = []
    for s, rs in rows.items():
        for r in rs:
            t, kind = decision_point(T[r["episode_id"]])
            dlg = [Turn("user" if x["actor"] == "shopper" else "assistant", x["text"], f"s{x['seq']}")
                   for x in T[r["episode_id"]] if x["kind"] == "message" and x["actor"] in ("shopper", "agent")
                   and (x["text"] or "").strip() and x["seq"] < t]
            if not any(d.role == "user" for d in dlg):
                raise SystemExit(f"{r['episode_id']}: no shopper turn before t")
            items.append((s, r, t, kind, dlg))
    if a.dry_run:
        chars = sum(len(PlainLLM.__doc__ or "") + sum(len(d.text) for d in dlg) for *_, dlg in items)
        print(json.dumps({"calls": len(items), "dialogue_chars": chars}))
        return
    for s in SETS:
        assert not (OUT / f"plain_{s}.jsonl").exists(), f"refusing to overwrite plain_{s}.jsonl"
    llm = OpenAIResponses(a.model, RES / "ledger_plain_truncated.jsonl", a.budget)

    def job(it):
        s, r, t, kind, dlg = it
        try:
            return PlainLLM(llm).run(dlg)
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001
            return e
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        res = list(ex.map(job, items))
    summ = {"model": a.model, "calls": len(items), "failed": [], "sets": {}}
    for s in SETS:
        out, tab = [], {"legit": Counter(), "viol": Counter()}
        for (s2, r, t, kind, dlg), pl in zip(items, res):
            if s2 != s:
                continue
            if isinstance(pl, Exception):
                summ["failed"].append({"episode_id": r["episode_id"], "error": repr(pl)})
                continue
            cart = R.cart_lines(D.load_cart(r["episode_id"]))
            d, codes = cart_check(Ledger(1, tuple(state_to_entries(pl["state"]).values())), cart)
            dec = verdict.plan_v3(None, d)
            grp = "legit" if r["outcome"] in R.LEGIT else "viol"
            tab[grp][dec] += 1
            out.append({"episode_id": r["episode_id"], "outcome": r["outcome"], "t_kind": kind, "decision": dec,
                        "codes": codes, "orig_decision": r["arms"]["plain"]["decision"], "plain_state": pl["state"],
                        "cost_usd": pl["cost_usd"]})
        (OUT / f"plain_{s}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out),
                                              encoding="utf-8", newline="\n")
        summ["sets"][s] = {k: dict(v) for k, v in tab.items()} | {"changed": sum(x["decision"] != x["orig_decision"] for x in out)}
    summ["cost_usd"] = round(sum(x.get("cost_usd", 0) for x in res if isinstance(x, dict)), 6)
    summ["cache_hits"] = llm.cache_hits
    (OUT / "plain_summary.json").write_text(json.dumps(summ, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
