"""G1v2 (original wording): FnCTOD + plain-LLM extraction, then the four PLAN_v3 arms with FROZEN rules.

Arms (unchanged PLAN_v3 code: cdv/extract.py, cdv/pipeline.py, cdv/m1.py; decision via cdv/verdict.py):
  plain | fnctod | fnctod_r (rules) | fnctod_rn (rules + NLI)
Inputs: the generated dialogue only (gold is used for scoring). Case files must match the manifest sha256.
Scoring per case (gold by construction, results/g1v2_20261126/PLAN_P3a_G1v2_original.md):
  final_ok      final budget (and quantity for P1) equals gold
  steps_ok      every user turn's ledger equals the per-turn gold (L2 multi-change; plain has no per-turn state)
  preserved     a condition that should stay (N0, S1, S2, U2 budget; P1 quantity) is unchanged
  asked         the arm asks (M1 hint CLARIFY); 'unnecessary' when the case expects no question
Usage:
  dry:  .venv/Scripts/python.exe eval/g1v2/run_g1v2.py --split dev --dry-run
  live: .venv/Scripts/python.exe eval/g1v2/run_g1v2.py --split dev --budget 0.20 ; then --split eval --budget 0.40
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "e_m1"))
import run as R  # noqa: E402  (DryLLM)
from cdv.extract import FnCTOD, OpenAIResponses, PlainLLM, Turn  # noqa: E402
from cdv.m1 import UserTurn  # noqa: E402
from cdv.pipeline import run_verified, state_to_entries  # noqa: E402

GEN = Path(r"C:/ct/runs/cdv_wallet/generated/G1v2")
OUT = ROOT / "results" / "g1v2_20261126"
ARMS = ("plain", "fnctod", "fnctod_r", "fnctod_rn")
PC = "set_purchase_conditions"


def vals(entries: dict) -> dict:
    by = {e.field: e.value for e in entries.values()} if isinstance(entries, dict) else {e.field: e.value for e in entries}
    return {"budget_max": by.get("budget_max"), "quantity": by.get("quantity")}


def eq(a, b):
    if b is None:
        return True
    return a is not None and abs(float(a) - float(b)) <= 1.0


def score(case, final: dict, steps: list | None, asked: bool):
    g = case["gold"]
    f = g["final"]
    final_ok = eq(final.get("budget_max"), f["budget_max"]) and eq(final.get("quantity"), f.get("quantity"))
    steps_ok = None
    if steps is not None:
        steps_ok = len(steps) == len(g["per_user_turn"]) and all(
            eq(s.get("budget_max"), p["budget_max"]) and eq(s.get("quantity"), p.get("quantity"))
            for s, p in zip(steps, g["per_user_turn"]))
    B0 = g["per_user_turn"][0]["budget_max"]
    tp = case["type"]
    preserved = None
    if tp in ("N0", "S1", "S2", "U2"):
        preserved = eq(final.get("budget_max"), B0)
    elif tp == "P1":
        preserved = eq(final.get("quantity"), 2)
    return {"final_ok": final_ok, "steps_ok": steps_ok, "preserved": preserved, "asked": asked,
            "unnecessary_question": asked and g["expect_no_question"]}


def evaluate(case, fn, pl, nli):
    users = [t for t in case["dialogue"] if t["role"] == "user"]
    ut = [UserTurn(t["turn_id"], int(t["turn_id"][1:]), t["text"]) for t in users]
    st = [dict(s, seq=int(s["turn_id"][1:])) for s in fn]
    out = {}
    out["plain"] = score(case, vals(state_to_entries(pl["state"])), None, False)
    out["fnctod"] = score(case, vals(state_to_entries(st[-1]["state"])) if st else {},
                          [vals(state_to_entries(s["state"])) for s in st], False)
    brands = sorted({str(b) for s in st for k in ("brand_include", "brand_exclude")
                     for b in ((s["state"].get(PC) or {}).get(k) or [])})
    for name, use in (("fnctod_r", None), ("fnctod_rn", nli)):
        res = run_verified(st, ut, nli=use, known_brands=brands)
        steps = []
        for tr in res["trace"]:
            led = tr["ledger"]
            steps.append({"budget_max": led.get("budget"), "quantity": led.get("qty")})
        out[name] = score(case, vals(res["ledger"].entries), steps, res["hint"] == "CLARIFY")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "eval"], required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default="gpt-6-luna")
    ap.add_argument("--budget", type=float, default=0.40)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--no-nli", action="store_true")
    a = ap.parse_args()
    man = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    path = GEN / f"{a.split}.jsonl"
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha != man["splits"][a.split]["file_sha256"]:
        raise SystemExit(f"case file sha256 {sha} != manifest")
    cases = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l]
    for c in cases:
        if not any(t["role"] == "user" for t in c["dialogue"]):
            raise SystemExit(f"{c['case_id']}: empty dialogue")
    tag = a.split + ("_dry" if a.dry_run else "")
    assert a.dry_run or not (OUT / f"rows_{tag}.jsonl").exists(), f"refusing to overwrite rows_{tag}.jsonl"
    llm = R.DryLLM() if a.dry_run else OpenAIResponses(a.model, OUT / "ledger.jsonl", a.budget)

    def job(c):
        dlg = [Turn(t["role"], t["text"], t["turn_id"]) for t in c["dialogue"]]
        try:
            return c["case_id"], (FnCTOD(llm).run(dlg), PlainLLM(llm).run(dlg))
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001
            return c["case_id"], e
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        ext = dict(ex.map(job, cases))
    nli = None
    if not a.no_nli and not a.dry_run:
        from cdv.nli import NLI
        nli = NLI()
    rows, failed = [], []
    for c in cases:
        v = ext[c["case_id"]]
        if isinstance(v, Exception):
            failed.append({"case_id": c["case_id"], "error": repr(v)})
            continue
        fn, pl = v
        row = {"case_id": c["case_id"], "type": c["type"],
               "fnctod_states": [{"turn_id": s["turn_id"], "selected": s.get("selected"), "state": s["state"]} for s in fn],
               "plain_state": pl["state"], "cost_usd": round(sum(s["cost_usd"] for s in fn) + pl["cost_usd"], 6)}
        if not a.dry_run:
            row["arms"] = evaluate(c, fn, pl, nli)
        rows.append(row)
    (OUT / f"rows_{tag}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                           encoding="utf-8", newline="\n")
    summ = {"split": a.split, "n": len(rows), "failed": failed, "dry_run": a.dry_run, "case_file_sha256": sha}
    if a.dry_run:
        summ["dry_run_estimate"] = {"calls_lower_bound": llm.calls, "input_tokens_est": int(llm.chars_in / 4),
                                    "note": "dry answers select no function, so FnCTOD argument calls are not counted"}
    else:
        summ["cost_usd"] = round(sum(r["cost_usd"] for r in rows), 6)
        summ["cache_hits"] = llm.cache_hits
        tab = defaultdict(lambda: defaultdict(Counter))
        for r in rows:
            for arm, s in r["arms"].items():
                for k, v in s.items():
                    if v is not None:
                        tab[(r["type"], arm)][k][bool(v)] += 1
        summ["by_type_arm"] = {f"{tp}|{arm}": {k: f"{v[True]}/{v[True] + v[False]}" for k, v in d.items()}
                               for (tp, arm), d in sorted(tab.items())}
    (OUT / f"summary_{tag}.json").write_text(json.dumps(summ, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in summ.items() if k != "by_type_arm"}))


if __name__ == "__main__":
    main()
