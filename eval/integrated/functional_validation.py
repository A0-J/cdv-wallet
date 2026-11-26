"""Integrated pipeline: no-cost functional test on VALIDATION (no model calls; nothing here tunes a rule on test).

(a) pilot: the 10 validation journeys that already have real FnCTOD output (PLAN_v3 pilot 2) -> all arms
    B0-B4 + U reference, with NLI. Wiring check only (n = 10).
(b) reference-mandate sweep: every validation baseline journey with a cart -> U reference arm only
    (hidden-spec gold conditions -> mandate -> full M2 gate). Gold is the INPUT here, so this is not a
    result of the proposed method; it measures (1) that the gate runs on CartTrace at scale (capture,
    binding, NOT_CAPTURED, UNKNOWN_ATTR rates on clean data) and (2) whether CartTrace RIGHT/WRONG means a
    payment-authority violation: how many WRONG carts a correct mandate can block at payment time.
Output: results/integrated_functional_20261126/{summary.json, pilot_rows.jsonl}
Usage:  .venv/Scripts/python.exe eval/integrated/functional_validation.py
"""
from __future__ import annotations

import glob
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "integrated"))
sys.path.insert(0, str(ROOT / "eval" / "e_m1"))
import arms as A  # noqa: E402
import env as E  # noqa: E402
import run as R  # noqa: E402  (gold_fields: scoring/reference only)

OUT = ROOT / "results" / "integrated_functional_20261126"
RES = ROOT / "results" / "e_m1_20261126"


def code_family(codes):
    fam = set()
    for c in codes:
        c = str(c)
        fam.add(c.split(":")[0] if not c.startswith("AVIP_") else "AVIP")
    return sorted(fam)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    from cdv.nli import NLI
    nli = NLI()
    summ = {"note": __doc__.split("\n\n")[0], "model_calls": 0}
    # (a) pilot
    rows = [json.loads(l) for l in (RES / "rows_R1_validation.jsonl").read_text(encoding="utf-8").splitlines() if l]
    cases = E.build_cases({r["episode_id"] for r in rows})
    pilot = []
    t0 = time.perf_counter()
    for r in rows:
        c = cases[r["episode_id"]]
        o = A.run_arms(c, r["fnctod_states"], nli=nli, gold=R.gold_fields(json.loads(c.scoring["hidden_spec"])))
        pilot.append({"episode_id": r["episode_id"], "outcome": c.scoring["outcome"], "t_kind": c.t_kind, **o})
    summ["pilot"] = {"n": len(pilot), "seconds": round(time.perf_counter() - t0, 1),
                     "decisions": {arm: dict(Counter(p["arms"][arm]["decision"] for p in pilot)) for arm in A.ARMS},
                     "U_reference": dict(Counter(p["U_reference"]["decision"] for p in pilot))}
    (OUT / "pilot_rows.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False, default=str) + "\n" for p in pilot),
                                          encoding="utf-8", newline="\n")
    # (b) reference sweep over validation
    eids = []
    for f in glob.glob(str(E.DATA / "messages" / "*" / "validation-*.parquet")):
        for m in pq.read_table(f, columns=["episode_id", "kind", "final_cart"]).to_pylist():
            if m["kind"] == "baseline" and (json.loads(m["final_cart"] or "{}").get("lines") or []):
                eids.append(m["episode_id"])
    msgs, turns = E.load_rows(set(eids))
    tab = defaultdict(Counter)
    fam = defaultdict(Counter)
    stops = Counter()
    t0 = time.perf_counter()
    for e in sorted(eids):
        try:
            c = E.build_case(e, msgs[e], turns[e])
        except E.InputError as ex:
            stops[str(ex).split(":", 1)[1].strip()[:40]] += 1
            continue
        env = A.Env(c)
        g = R.gold_fields(json.loads(c.scoring["hidden_spec"]))
        d, codes = env.full_gate(A.ledger_to_mandate(A.gold_ctx(g), c.reg, c.seller, f"m-{e}", 1, env.session))
        out = c.scoring["outcome"]
        tab[out][d] += 1
        for f_ in code_family(codes):
            fam[out][f_] += 1
        fam[out]["E2_fires"] += env.e2
    summ["reference_sweep_validation"] = {
        "journeys_with_cart": len(eids), "input_stops": dict(stops), "seconds": round(time.perf_counter() - t0, 1),
        "decision_by_outcome": {k: dict(v) for k, v in sorted(tab.items())},
        "code_families_by_outcome": {k: dict(v) for k, v in sorted(fam.items())}}
    (OUT / "summary.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summ, indent=1, ensure_ascii=False)[:5000])


if __name__ == "__main__":
    main()
