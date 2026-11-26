"""Development evaluation on VALIDATION (no model calls): arms B0-B4 on the P2 extraction.

Rows: results/integrated_dev_20261126/extract_{V1,V3,V2}.jsonl (FnCTOD states and plain state, dialogue cut at t).
Arms: eval/integrated/arms.py (B0-B4) + U reference (gold conditions -> mandate; never a runtime input) +
      bridge row 'v1' = PLAN_v3 rules (cdv/pipeline.py::run_verified, rules+NLI) + M2a cart check on the same
      truncated states (cdv.verdict.plan_v3), so v1 and v2 are compared on identical inputs.
Ground truth for transactions (provisional, user-utterance labels not yet made):
  outcome: CartTrace RIGHT/RIGHT_BY_LUCK = legit, WRONG/WRONG_HIDDEN = violating (known to be a weak label:
           most WRONG carts break no payment-checkable condition, results/integrated_functional_20261126)
  pay_viol: the U reference arm denies the cart (a stated budget/quantity/brand/bundle-count condition is broken)
Also: CLARIFY causes (M1 dependency / UNKNOWN_ATTR / E2 / other gate), paired McNemar between arms,
reference-resolution counts for the option-B criterion (denominator: reference turns with an agent list).
This is development data: thresholds may be set here; nothing here is a final result.
Output: results/integrated_dev_20261126/{dev_rows.jsonl, dev_summary.json, DEV_TABLES.md}
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
for p in ("eval/integrated", "eval/e_m1"):
    sys.path.insert(0, str(ROOT / p))
import arms as A  # noqa: E402
import env as E  # noqa: E402
import run as R  # noqa: E402
from cdv import verdict  # noqa: E402
from cdv.m1 import Ledger  # noqa: E402
from cdv.pipeline import cart_check, run_verified  # noqa: E402
from cdv.v2.candidates import ENUM, REF, resolve_turn  # noqa: E402

DEV = ROOT / "results" / "integrated_dev_20261126"
SETS = ("V1", "V3", "V2")
ARMS = ("B0", "B1", "B2", "B3", "B4", "v1")
LEGIT, VIOL = {"RIGHT", "RIGHT_BY_LUCK"}, {"WRONG", "WRONG_HIDDEN"}
PC = "set_purchase_conditions"


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * max(0, c - h), 1), round(100 * min(1, c + h), 1)]


def mcnemar(a_blocks, b_blocks):
    """Exact two-sided McNemar on paired binary outcomes (blocked or not)."""
    b = sum(1 for x, y in zip(a_blocks, b_blocks) if x and not y)
    c = sum(1 for x, y in zip(a_blocks, b_blocks) if y and not x)
    n = b + c
    if n == 0:
        return {"a_only": b, "b_only": c, "p": 1.0}
    k = min(b, c)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    return {"a_only": b, "b_only": c, "p": round(p, 4)}


def clarify_cause(a):
    if a["decision"] != "CLARIFY":
        return None
    if a.get("m1_asks"):
        return "M1"
    codes = a.get("codes") or []
    if any(str(c).startswith("UNKNOWN_ATTR") for c in codes):
        return "UNKNOWN_ATTR"
    if any(str(c).startswith("E2_") for c in codes):
        return "E2"
    return "gate_other"


def ref_stats(case):
    """Reference turns (option-B criterion): with an agent list / all; resolved to a catalog product."""
    c = Counter()
    for u in case.user_turns:
        if not REF.search(u.text or ""):
            continue
        last = next((x for s, x in sorted(case.agent_turns, key=lambda z: -z[0]) if s < u.seq), None)
        has_list = bool(last and ENUM.findall(last))
        r = resolve_turn(u.text, last, u.seq, case.reg)
        c["ref_all"] += 1
        c["ref_with_list"] += has_list
        c["resolved_all"] += r.status == "RESOLVED"
        c["resolved_with_list"] += r.status == "RESOLVED" and has_list
    return c


def main():
    from cdv.nli import NLI
    nli = NLI()
    rows = []
    for s in SETS:
        rows += [json.loads(l) for l in (DEV / f"extract_{s}.jsonl").read_text(encoding="utf-8").splitlines() if l]
    cases = E.build_cases({r["episode_id"] for r in rows})
    out, refc = [], Counter()
    t0 = time.perf_counter()
    for r in rows:
        c = cases[r["episode_id"]]
        assert abs(c.t - r["t"]) < 1e-9, f"decision point differs from extraction for {r['episode_id']}"
        g = R.gold_fields(json.loads(c.scoring["hidden_spec"]))
        t1 = time.perf_counter()
        o = A.run_arms(c, r["fnctod_states"], nli=nli, gold=g)
        ms_v2 = round(1000 * (time.perf_counter() - t1), 1)
        # bridge: PLAN_v3 rules + M2a on the same truncated states
        st = [dict(x, seq=int(x["turn_id"][1:])) for x in r["fnctod_states"] if int(x["turn_id"][1:]) < c.t]
        brands = sorted({str(b) for x in st for k in ("brand_include", "brand_exclude")
                         for b in ((x["state"].get(PC) or {}).get(k) or [])})
        cart = R.cart_lines(c.scoring["final_cart"])          # exactly the PLAN_v3 cart input
        v1 = run_verified(st, c.user_turns, nli=nli, known_brands=brands)
        d1, codes1 = cart_check(v1["ledger"], cart)
        o["arms"]["v1"] = {"decision": verdict.plan_v3(v1["hint"], d1), "codes": codes1, "m1_asks": v1["hint"] == "CLARIFY"}
        refc += ref_stats(c)
        out.append({"episode_id": r["episode_id"], "set": r["set"], "outcome": r["outcome"], "t_kind": c.t_kind,
                    "pay_viol": o["U_reference"]["decision"] == "DENY", "ms_all_arms": ms_v2, **o})
    secs = round(time.perf_counter() - t0, 1)
    (DEV / "dev_rows.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False, default=str) + "\n" for x in out),
                                        encoding="utf-8", newline="\n")
    summ = {"note": __doc__.split("\n\n")[0], "model_calls": 0, "n": len(out), "seconds": secs,
            "sets": dict(Counter(x["set"] for x in out)), "reference_turns": dict(refc), "groups": {}}
    groups = {"legit(outcome)": [x for x in out if x["outcome"] in LEGIT],
              "violating(outcome)": [x for x in out if x["outcome"] in VIOL],
              "pay_viol(U denies)": [x for x in out if x["pay_viol"]],
              "violating_not_pay_checkable": [x for x in out if x["outcome"] in VIOL and not x["pay_viol"]]}
    for gname, G in groups.items():
        summ["groups"][gname] = {"n": len(G)}
        for arm in ARMS:
            dec = Counter(x["arms"][arm]["decision"] for x in G)
            blocked = sum(v for k, v in dec.items() if k != "ALLOW")
            causes = Counter(clarify_cause(x["arms"][arm]) for x in G if x["arms"][arm]["decision"] == "CLARIFY")
            summ["groups"][gname][arm] = {"ALLOW": dec["ALLOW"], "CLARIFY": dec["CLARIFY"], "DENY": dec["DENY"],
                                          "blocked_pct": round(100 * blocked / len(G), 1) if G else None,
                                          "blocked_ci95": wilson(blocked, len(G)), "clarify_causes": dict(causes)}
    L, V = groups["legit(outcome)"], groups["pay_viol(U denies)"]
    blk = lambda G, a: [x["arms"][a]["decision"] != "ALLOW" for x in G]  # noqa: E731
    summ["mcnemar_legit_blocked"] = {f"{a} vs {b}": mcnemar(blk(L, a), blk(L, b))
                                     for a, b in (("B3", "B4"), ("B3", "B2"), ("B3", "v1"), ("B4", "B1"))}
    summ["mcnemar_payviol_blocked"] = {f"{a} vs {b}": mcnemar(blk(V, a), blk(V, b))
                                       for a, b in (("B3", "B2"), ("B3", "B1"), ("B3", "B0"))}
    m1u = Counter(k for x in out for (_, k, _) in x["m1"]["unresolved"])
    m1r = Counter(code for x in out for (_, code) in x["m1"]["rejected"])
    summ["m1_items"] = {"unresolved_by_kind": dict(m1u), "rejected_by_code": dict(m1r),
                        "selection_how": dict(Counter(x["m1"]["selection_how"] for x in out)),
                        "deferred_fields": dict(Counter(f for x in out for f in x["arms"]["B3"].get("deferred", [])))}
    summ["ms_all_arms_median"] = sorted(x["ms_all_arms"] for x in out)[len(out) // 2]
    (DEV / "dev_summary.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summ, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
