"""P2: validation development extraction for M1 v2 / integrated evaluation (FnCTOD + plain LLM).

Sets (validation only; seeded; no test data):
  V1  R1-type: baseline journeys with a stated non-substitute condition (eval/e_m1/run.py::select "R1")
  V3  R3-type: baseline journeys with a stockout fault                   (run.py::select "R3")
  V2  R2-type: shopper picks, then declines (run.py PICK/DECL rule), validation split only
Input to the extractor: shopper/agent messages BEFORE the decision point t (shared decision_point), so
no post-request utterance reaches any arm. Extraction only; evaluation is a separate no-cost step.
Output: results/integrated_dev_20261126/{extract_<set>.jsonl, extract_summary_<set>.json, ledger.jsonl}
Usage:
  dry:  .venv/Scripts/python.exe eval/integrated/extract_dev.py --set V1 --n 200 --dry-run
  live: .venv/Scripts/python.exe eval/integrated/extract_dev.py --set V1 --n 200 --budget 1.0  (after approval)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "e_m1"))
sys.path.insert(0, str(ROOT / "eval" / "m1_v2"))
import diagnose as D  # noqa: E402
import run as R  # noqa: E402
from cdv.extract import OpenAIResponses, Turn  # noqa: E402
from recompute_truncated import decision_point  # noqa: E402

OUT = ROOT / "results" / "integrated_dev_20261126"
SPLIT = "validation"


def select_set(name, n):
    rows = R.load_messages([SPLIT])
    if name in ("V1", "V3"):
        return R.select("R1" if name == "V1" else "R3", SPLIT, n, rows)
    cand = {r["episode_id"]: r for r in rows if r["sub_kind"] == "checkout"
            or any(f.get("kind") == "stockout" for f in json.loads(r["hidden_spec"]).get("faults") or [])}
    dl = R.load_dialogues(set(cand), [SPLIT])
    chosen = []
    for e, d in dl.items():
        sh = [x for x in d if x["actor"] == "shopper"][1:]
        p = [i for i, x in enumerate(sh) if R.PICK.search(x["text"])]
        q = [i for i, x in enumerate(sh) if R.DECL.search(x["text"])]
        if p and q and min(p) < max(q) and cand[e]["outcome_class"] in R.LEGIT | R.VIOL and R.cart_lines(cand[e]["final_cart"]):
            chosen.append(cand[e])
    chosen.sort(key=lambda r: r["episode_id"])
    return chosen[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["V1", "V2", "V3"], required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default="gpt-6-luna")
    ap.add_argument("--budget", type=float, default=1.0)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    sample = select_set(a.set, a.n)
    eids = {r["episode_id"] for r in sample}
    T = D.load_turns(eids, splits=(SPLIT,))
    miss = sorted(eids - set(T))
    if miss:
        raise SystemExit(f"{len(miss)} selected journeys have no turns: {miss[:5]}")
    items = []
    for r in sample:
        t, kind = decision_point(T[r["episode_id"]])
        dlg = [x for x in T[r["episode_id"]] if x["kind"] == "message" and x["actor"] in ("shopper", "agent")
               and (x["text"] or "").strip() and x["seq"] < t]
        if not any(x["actor"] == "shopper" for x in dlg):
            raise SystemExit(f"{r['episode_id']}: no shopper turn before t")
        items.append((r, t, kind, dlg))
    tag = f"{a.set}" + ("_dry" if a.dry_run else "")
    OUT.mkdir(parents=True, exist_ok=True)
    assert a.dry_run or not (OUT / f"extract_{tag}.jsonl").exists(), f"refusing to overwrite extract_{tag}.jsonl"
    llm = R.DryLLM() if a.dry_run else OpenAIResponses(a.model, OUT / "ledger.jsonl", a.budget)
    ext = R.parallel_extract([(r["episode_id"], dlg) for r, t, kind, dlg in items], llm, llm, a.workers)
    failed = [{"episode_id": e, "error": repr(v)} for e, v in ext.items() if isinstance(v, Exception)]
    out = []
    for r, t, kind, dlg in items:
        v = ext[r["episode_id"]]
        if isinstance(v, Exception):
            continue
        fn, pl, t_fn = v
        out.append({"episode_id": r["episode_id"], "set": a.set, "outcome": r["outcome_class"], "t": t, "t_kind": kind,
                    "n_user_turns_before_t": sum(1 for x in dlg if x["actor"] == "shopper"),
                    "fnctod_states": [{"turn_id": s["turn_id"], "selected": s.get("selected"), "state": s["state"]} for s in fn],
                    "plain_state": pl["state"], "cost_usd": round(sum(s["cost_usd"] for s in fn) + pl["cost_usd"], 6),
                    "extract_s": round(t_fn, 3)})
    (OUT / f"extract_{tag}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out),
                                              encoding="utf-8", newline="\n")
    summ = {"set": a.set, "split": SPLIT, "n_selected": len(sample), "n_done": len(out), "failed": failed,
            "outcomes": {o: sum(1 for x in out if x["outcome"] == o) for o in sorted({x["outcome"] for x in out})},
            "dry_run": a.dry_run, "model": None if a.dry_run else a.model}
    if a.dry_run:
        summ["dry_run_estimate"] = {"calls_lower_bound": llm.calls, "input_tokens_est": int(llm.chars_in / 4),
                                    "user_turns_before_t": sum(x["n_user_turns_before_t"] for x in out)}
    else:
        summ["cost_usd"] = round(sum(x["cost_usd"] for x in out), 6)
        summ["cache_hits"] = llm.cache_hits
    (OUT / f"extract_summary_{tag}.json").write_text(json.dumps(summ, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in summ.items() if k != "failed"}))


if __name__ == "__main__":
    main()
