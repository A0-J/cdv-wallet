"""Exact reproduction of the PLAN_v3 result rows (no model calls). Regression gate for all later work.

For every stored row the frozen PLAN_v3 code path is run again on the stored extractor outputs:
  R1/R3/R2 test_cross_store, R1 validation  -> eval/e_m1/run.py::run_journey (unchanged)
  G1 eval                                    -> eval/e_m1/run.py::run_g1 with FnCTOD/PlainLLM replaced by
                                                stubs that return the stored outputs (no network)
Pass criterion: every field equal, except run-time measurements (cost_usd, extract_s, verify_ms).
"Almost equal" is a failure. Also checks that cdv.verdict.plan_v3 gives every stored arm decision.

Data reading: dialogues and messages are read from ALL four splits and every episode must be found
(the single-split read error of 2026-11-26 cannot recur silently).
Output: results/regress_20261126/reproduce_plan_v3.json ; exit code 1 on any mismatch.
Usage:  .venv/Scripts/python.exe eval/regress/reproduce_plan_v3.py [--no-nli-sets]
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "e_m1"))
import run as R  # noqa: E402  (frozen PLAN_v3 harness)
from cdv import verdict  # noqa: E402

RES = ROOT / "results" / "e_m1_20261126"
OUT = ROOT / "results" / "regress_20261126"
SPLITS = ("train", "validation", "test_cross_store", "test_cross_template")
SETS = ["R1_test_cross_store", "R3_test_cross_store", "R2_test_cross_store", "R1_validation"]
VOLATILE = {"cost_usd", "extract_s", "verify_ms"}
SAVE = None


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in VOLATILE}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def norm(x):
    return json.loads(json.dumps(x, ensure_ascii=False, default=str))


def load_msgs(eids):
    out = {}
    cols = ["episode_id", "hidden_spec", "kind", "sub_kind", "outcome_class", "final_cart", "template_family", "split"]
    for s in SPLITS:
        for f in sorted(glob.glob(str(R.DATA / "messages" / "*" / f"{s}-*.parquet"))):
            for r in pq.read_table(f, columns=cols, filters=[("episode_id", "in", list(eids))]).to_pylist():
                out[r["episode_id"]] = r
    return out


def diff(a, b, path=""):
    if type(a) is not type(b):
        return [f"{path}: type {type(a).__name__} != {type(b).__name__}"]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}.{k}: missing on one side")
            else:
                out += diff(a[k], b[k], f"{path}.{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: len {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diff(x, y, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def check_verdicts(row):
    bad = []
    for arm, a in row["arms"].items():
        m2a = "ALLOW" if not a["codes"] else "DENY"
        hint = a["hint"] if arm in ("fnctod_r", "fnctod_rn") else None
        if verdict.plan_v3(hint, m2a) != a["decision"]:
            bad.append(f"{row['episode_id']}:{arm}: verdict.plan_v3 -> {verdict.plan_v3(hint, m2a)} != {a['decision']}")
    return bad


def reproduce_set(name, nli):
    rows = [json.loads(l) for l in (RES / f"rows_{name}.jsonl").read_text(encoding="utf-8").splitlines() if l]
    eids = {r["episode_id"] for r in rows}
    msgs = load_msgs(eids)
    dl = R.load_dialogues(eids, SPLITS)
    missing = sorted(eids - set(msgs)) + sorted(eids - set(dl))
    if missing:
        raise SystemExit(f"{name}: episodes not found in any split: {missing[:5]} ({len(missing)})")
    mism, vbad, new_rows = [], [], []
    for r in rows:
        fn = [{"turn_id": s["turn_id"], "selected": s["selected"], "state": s["state"], "cost_usd": 0.0}
              for s in r["fnctod_states"]]
        out = R.run_journey(msgs[r["episode_id"]], dl[r["episode_id"]], (fn, {"state": r["plain_state"], "cost_usd": 0.0}, 0.0), nli)
        d = diff(strip(norm(r)), strip(norm(out)))
        if d:
            mism.append({"episode_id": r["episode_id"], "diffs": d[:10]})
        vbad += check_verdicts(r)
        if SAVE:
            new_rows.append(norm(out))
    if SAVE:
        SAVE.mkdir(parents=True, exist_ok=True)
        (SAVE / f"rows_{name}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in new_rows), encoding="utf-8", newline="\n")
    return {"n": len(rows), "mismatched_rows": len(mism), "examples": mism[:5], "verdict_mismatches": vbad[:10],
            "n_verdict_mismatches": len(vbad)}


def reproduce_g1(nli):
    rows = [json.loads(l) for l in (RES / "rows_G1_eval.jsonl").read_text(encoding="utf-8").splitlines() if l]
    cases = [json.loads(l) for l in R.G1_FILE.read_text(encoding="utf-8").splitlines()][:len(rows)]
    by_case = {r["case_id"]: r for r in rows}
    assert [c["case_id"] for c in cases] == [r["case_id"] for r in rows], "G1 case order differs from stored rows"
    # identical dialogues exist (e.g. same base opening + same template turn); with workers=1 run_g1 calls the
    # stub in case order, so each key holds a queue of case ids consumed in that order
    key_to_cases = {}
    for c in cases:
        key = tuple([c["user_turns"][0]["text"]] + [x["text"] for x in c.get("external_texts") or []]
                    + [u["text"] for u in c["user_turns"][1:]])
        key_to_cases.setdefault(key, []).append(c["case_id"])
    fn_q = {k: list(v) for k, v in key_to_cases.items()}
    pl_q = {k: list(v) for k, v in key_to_cases.items()}

    class FnStub:
        def __init__(self, llm):
            pass

        def run(self, dialogue):
            r = by_case[fn_q[tuple(t.text for t in dialogue)].pop(0)]
            return [{"turn_id": s["turn_id"], "selected": s["selected"], "state": s["state"]} for s in r["fnctod_states"]]

    class PlainStub:
        def __init__(self, llm):
            pass

        def run(self, dialogue):
            return {"state": by_case[pl_q[tuple(t.text for t in dialogue)].pop(0)]["plain_state"]}

    R.FnCTOD, R.PlainLLM = FnStub, PlainStub
    out, failed = R.run_g1(None, None, nli, len(rows), workers=1)
    assert not failed, failed
    if SAVE:
        SAVE.mkdir(parents=True, exist_ok=True)
        (SAVE / "rows_G1_eval.jsonl").write_text("".join(json.dumps(norm(x)) + "\n" for x in out), encoding="utf-8", newline="\n")
    mism = []
    for a, b in zip(rows, out):
        d = diff(strip(norm(a)), strip(norm(b)))
        if d:
            mism.append({"case_id": a["case_id"], "diffs": d[:10]})
    return {"n": len(rows), "mismatched_rows": len(mism), "examples": mism[:5]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="*", default=SETS + ["G1_eval"])
    ap.add_argument("--save", default="", help="also write the recomputed rows to results/regress_20261126/rerun_<save>/")
    a = ap.parse_args()
    global SAVE
    SAVE = (OUT / f"rerun_{a.save}") if a.save else None
    from cdv.nli import NLI
    nli = NLI()
    res = {"note": __doc__.split("\n\n")[0], "sets": {}}
    for s in a.sets:
        res["sets"][s] = reproduce_g1(nli) if s == "G1_eval" else reproduce_set(s, nli)
        print(s, json.dumps({k: v for k, v in res["sets"][s].items() if k != "examples"}), flush=True)
    ok = all(v["mismatched_rows"] == 0 and v.get("n_verdict_mismatches", 0) == 0 for v in res["sets"].values())
    res["exact_reproduction"] = ok
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (f"reproduce_plan_v3_{a.save}.json" if a.save else "reproduce_plan_v3.json")).write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("EXACT" if ok else "MISMATCH")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
