"""Review item 4: M1-G run-to-run non-determinism on the v4 dev fault-injection path (no model calls).

Uses the two existing M1-G runs of a prompt version (default v2 = the frozen prompt;
results/m1g_20261126/prompt_v2/rows_dev.jsonl, columns m1g_run1 / m1g_run2) and the machinery of
eval/v4check/contamination.py (imported, not edited): prior = episode_gold.initial_state (oracle prior of the
injection design), candidate operations applied in evidence-turn order, ACCEPT -> applied, CLARIFY -> pending,
REJECT -> not applied; same real gate (Env.full_gate) and same B3-type (ask only if some combination of pending ops
changes the gate decision, combinations cut at 6 ops as in contamination.py) and B4-type (ask whenever pending) arms.
Reports: (1) candidate transition matrix run1 x run2 (all, by gold label); (2) verified state mismatch (episodes,
transactions); (3) mandate scope mismatch (ledger_to_mandate primary scope + clauses); (4) final decision mismatch per
transaction for B3-type and B4-type; (5) ALLOW <-> CLARIFY/DENY switches with the candidates whose decision flipped.
Output: results/review_20261127/m1g_det/nondet_{version}.json, NONDET_{version}.md
Usage: .venv/Scripts/python.exe eval/review/m1g_det/nondet.py [v2|v1]
"""
from __future__ import annotations

import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata", "eval/v4check"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import arms as A  # noqa: E402
import contamination as C  # noqa: E402
import run_ext as X  # noqa: E402
from cdv import verdict  # noqa: E402
from cdv.v2.integrate import ledger_to_mandate  # noqa: E402

V4 = C.V4
OUT = ROOT / "results" / "review_20261127" / "m1g_det"
D4 = ("ACCEPT", "REJECT", "CLARIFY", "UNSUPPORTED")


def mandate_key(env, case, cat, state):
    m = ledger_to_mandate(X.gold_ctx({"effective_state": state}, cat), case.reg, case.seller, f"m-{case.episode_id}", 1, env.session)
    return repr(m.primary) + "|" + repr(getattr(m, "clauses", None))


def decide_arms(env, case, cat, init, ops_dec):
    """ops_dec: list of (op, decision) in evidence order -> (final state, pending ops, B4-type, B3-type)."""
    st, pend = init, []
    for op, dec in ops_dec:
        if dec == "ACCEPT":
            st = C.apply(st, op)
        elif dec == "CLARIFY":
            pend.append(op)
    d0, c0 = C.gate(env, case, cat, st)
    b4 = verdict.integrated(d0, c0, bool(pend))
    if not pend:
        return st, pend, b4, verdict.integrated(d0, c0, False)
    outs = set()
    use = pend[:C.MAX_COMBO_OPS]
    for mask in itertools.product((0, 1), repeat=len(use)):
        s2 = st
        for on, op in zip(mask, use):
            if on:
                s2 = C.apply(s2, op)
        outs.add(C.gate(env, case, cat, s2)[0])
    b3 = "CLARIFY" if len(outs) > 1 else verdict.integrated(d0, c0, False)
    return st, pend, b4, b3


def main(version="v2"):
    rows_path = ROOT / "results" / "m1g_20261126" / ("prompt_v2" if version == "v2" else "") / "rows_dev.jsonl"
    rows = [json.loads(l) for l in rows_path.read_text(encoding="utf-8").splitlines() if l]
    eps = {e["episode_id"]: e for e in X.jl(V4 / "dev" / "episodes.jsonl")}
    eg = {g["episode_id"]: g for g in X.jl(V4 / "dev" / "episode_gold.jsonl")}
    tg = {g["transaction_id"]: g for g in X.jl(V4 / "dev" / "transaction_gold.jsonl")}
    excl = set(json.loads((ROOT / "results" / "extdata_20261126" / "exclusion_v4_dev.json").read_text(encoding="utf-8"))["excluded_episodes"])
    it = iter(rows)
    dec = {}
    for e, ep in eps.items():
        for k, op in enumerate(ep["candidate_operations"]):
            r = next(it)
            assert r["episode_id"] == e and r["field"] == op["field"] and r["op"] == op["operation"], "row order mismatch"
            dec[(e, k)] = r
    # (1) transition matrix
    trans = defaultdict(Counter)
    for (e, k), r in dec.items():
        if e in excl:
            continue
        for grp in ("ALL", f"label={r['label']}", f"cited={'user' if r['cited_role'] == 'user' else 'non-user'}"):
            trans[grp][(r["m1g_run1"], r["m1g_run2"])] += 1
    # per episode ordered ops with both runs
    ep_ops = {}
    for e, ep in eps.items():
        if e in excl:
            continue
        order = {x["turn_id"]: i for i, x in enumerate(ep["dialogue"])}
        ops = sorted(enumerate(ep["candidate_operations"]), key=lambda kv: order.get(kv[1]["evidence_turn_id"], 0))
        ep_ops[e] = [(k, op) for k, op in ops]
    st_mis_ep = sum(1 for e, ops in ep_ops.items()
                    if any(dec[(e, k)]["m1g_run1"] != dec[(e, k)]["m1g_run2"] for k, _ in ops))
    res_tx = []
    for tx in X.jl(V4 / "dev" / "transactions.jsonl"):
        e = tx["episode_id"]
        if e in excl:
            continue
        ep, g, gt = eps[e], eg[e], tg.get(tx["transaction_id"]) or {}
        cat = {c["sku"]: c for c in ep["catalog"]}
        case = X.build_case(ep, tx, gt)
        env = A.Env(case)
        out = {}
        for run in ("m1g_run1", "m1g_run2"):
            st, pend, b4, b3 = decide_arms(env, case, cat, g["initial_state"], [(op, dec[(e, k)][run]) for k, op in ep_ops[e]])
            out[run] = {"state": json.dumps(st, sort_keys=True), "pending": json.dumps(pend, sort_keys=True),
                        "mandate": mandate_key(env, case, cat, st), "B4": b4, "B3": b3}
        flips = [{"field": op["field"], "op": op["operation"], "label": dec[(e, k)]["label"],
                  "run1": dec[(e, k)]["m1g_run1"], "run2": dec[(e, k)]["m1g_run2"]}
                 for k, op in ep_ops[e] if dec[(e, k)]["m1g_run1"] != dec[(e, k)]["m1g_run2"]]
        res_tx.append({"transaction_id": tx["transaction_id"], "episode_id": e, "type": gt.get("transaction_type"),
                       "expected": gt.get("expected_checkout"), "follows_rejected": bool(gt.get("follows_rejected_proposal")),
                       "state_differs": out["m1g_run1"]["state"] != out["m1g_run2"]["state"],
                       "pending_differs": out["m1g_run1"]["pending"] != out["m1g_run2"]["pending"],
                       "mandate_differs": out["m1g_run1"]["mandate"] != out["m1g_run2"]["mandate"],
                       "B3": (out["m1g_run1"]["B3"], out["m1g_run2"]["B3"]), "B4": (out["m1g_run1"]["B4"], out["m1g_run2"]["B4"]),
                       "flips": flips})
    n = len(res_tx)
    summ = {"prompt_version": version, "rows_file": str(rows_path.relative_to(ROOT)), "episodes": len(ep_ops),
            "excluded": sorted(excl), "transactions": n,
            "candidates_both_runs": sum(trans["ALL"].values()),
            "candidate_agreement": sum(v for (a, b), v in trans["ALL"].items() if a == b),
            "episodes_with_any_flip": st_mis_ep,
            "tx_state_differs": sum(r["state_differs"] for r in res_tx),
            "tx_pending_differs": sum(r["pending_differs"] for r in res_tx),
            "tx_state_or_pending_differs": sum(r["state_differs"] or r["pending_differs"] for r in res_tx),
            "tx_mandate_differs": sum(r["mandate_differs"] for r in res_tx)}
    for arm in ("B3", "B4"):
        summ[f"tx_{arm}_decision_differs"] = sum(r[arm][0] != r[arm][1] for r in res_tx)
        summ[f"tx_{arm}_transitions"] = dict(Counter(f"{a}->{b}" for a, b in (r[arm] for r in res_tx) if a != b))
        summ[f"tx_{arm}_allow_switch"] = sum((a == "ALLOW") != (b == "ALLOW") for a, b in (r[arm] for r in res_tx))
        by = defaultdict(Counter)
        for r in res_tx:
            by[r["type"]][r[arm][0] != r[arm][1]] += 1
        summ[f"tx_{arm}_differs_by_type"] = {t: f"{c[True]}/{c[True] + c[False]}" for t, c in sorted(by.items(), key=lambda kv: str(kv[0]))}
    # causes of ALLOW switches (B3 and B4): flipped candidate (field, op, gold label, run1->run2)
    causes = {}
    for arm in ("B3", "B4"):
        cc = Counter()
        for r in res_tx:
            a, b = r[arm]
            if (a == "ALLOW") != (b == "ALLOW"):
                for f in r["flips"]:
                    cc[f"{f['field']}/{f['op']} gold={f['label']} {f['run1']}->{f['run2']}"] += 1
        causes[arm] = dict(cc.most_common())
    summ["allow_switch_flip_causes"] = causes
    summ["transition_matrix"] = {g: {f"{a}->{b}": v for (a, b), v in sorted(c.items())} for g, c in trans.items()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"nondet_{version}.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / f"nondet_rows_{version}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in res_tx),
                                                     encoding="utf-8", newline="\n")
    md = [f"# M1-G 두 회차 비결정성 (프롬프트 {version}, v4 dev 결함 주입 경로, 오라클 이전 상태, 모델 호출 0)", ""]
    for g in ("ALL", "label=ACCEPT", "label=REJECT", "label=CLARIFY", "cited=user", "cited=non-user"):
        c = trans.get(g)
        if not c:
            continue
        md += [f"## 전이 행렬 {g} (n={sum(c.values())}, 행 = 1회, 열 = 2회)", "", "| 1회 \\ 2회 | " + " | ".join(D4) + " |",
               "|---|" + "---:|" * len(D4)]
        for a in D4:
            if any(c.get((a, b)) for b in D4):
                md.append(f"| {a} | " + " | ".join(str(c.get((a, b), 0)) for b in D4) + " |")
        md.append("")
    md += ["## 장부·권한·판정 불일치", "", "```", json.dumps({k: v for k, v in summ.items() if k not in ("transition_matrix", "excluded")},
                                                         indent=1, ensure_ascii=False), "```"]
    (OUT / f"NONDET_{version}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in summ.items() if k not in ("transition_matrix", "excluded")}, indent=1, ensure_ascii=False))
    print(json.dumps(summ["transition_matrix"]["ALL"]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "v2")
