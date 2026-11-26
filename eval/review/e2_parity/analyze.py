"""Independent check (review items 7, 2a, 2b) on v4 dev — NO model calls, no existing file modified.

  E2      matched stockout rows: E2 firing (row 'e2_fires') separated from each arm's final decision, by intent case /
          reference verdict / evidence status; false positives (fired, reference ALLOW), misses (not fired, reference
          CLARIFY = premise not verified: cases 2-no-evidence and 4); rows whose final decision carries the E2 code
          (E2 is the last step of Env.full_gate and only turns ALLOW into CLARIFY, eval/integrated/arms.py:124).
  PARITY  what each side had: platform tool turns, seller tool turns, catalog stock 0, listing text (counts only).
  PLAIN+M2 exploratory arm: the one-shot PlainLLM state already stored in the P4 rows ('plain_state', extracted over the
          whole dialogue = the v4 decision point) -> raw_ctx -> ledger_to_mandate -> the same Env.full_gate, verdict
          'integrated' without M1. Two policies: 'record' (as the pre-freeze P4 rows) and 'consent_clarify' (as frozen
          610a97c: ALLOW with an unverified required condition at the consent point -> CLARIFY; every v4 checkout is a
          consent point). Also on validation (P2 plain_state, cut at t) when --validation is given.
Output: results/review_20261127/e2_parity/{e2.json, parity.json, plain_m2_v4dev.json, plain_m2_rows_{A,B}.jsonl, ...}
Usage: .venv/Scripts/python.exe eval/review/e2_parity/analyze.py [--validation]
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata", "eval/whisperbench"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import arms as A  # noqa: E402
import run_ext as X  # noqa: E402
from cdv import verdict  # noqa: E402

RES = ROOT / "results" / "extdata_20261126"
OUT = ROOT / "results" / "review_20261127" / "e2_parity"
V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4/dev")
E2CODE = "E2_STOCK_CLAIM_BY_CHOSEN"


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def e2_analysis(tags):
    out = {}
    for tag in tags:
        M = jl(RES / f"rows_v4_dev_{tag}_matched.jsonl")
        if not M:
            continue
        arms = [a for a in M[0]["arms"] if a in ("B2", "B3", "B4", "B3_v2")]
        by = defaultdict(list)
        for m in M:
            by[(m["intent_case"], m["reference_verdict"], m["evidence_status"])].append(m)
        cells = []
        for k, G in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
            row = {"case": k[0], "reference": k[1], "evidence": k[2], "n": len(G), "e2_fired": sum(bool(m["e2_fires"]) for m in G),
                   "by_similarity": {s: f"{sum(bool(m['e2_fires']) for m in G if m['pair_similarity'] == s)}/"
                                        f"{sum(1 for m in G if m['pair_similarity'] == s)}" for s in ("title_overlap", "type_only")}}
            for a in arms:
                dec = Counter(m["arms"][a]["decision"] for m in G)
                row[a] = {"final": dict(dec), "e2_code_in_final": sum(E2CODE in (m["arms"][a].get("codes") or []) for m in G)}
            cells.append(row)
        ref_allow = [m for m in M if m["reference_verdict"] == "ALLOW"]
        premise = [m for m in M if m["reference_verdict"] == "CLARIFY"]          # cases 2-no-evidence and 4
        deny = [m for m in M if m["reference_verdict"] == "DENY"]
        summ = {"n": len(M),
                "false_positive_fired_on_reference_ALLOW": f"{sum(bool(m['e2_fires']) for m in ref_allow)}/{len(ref_allow)}",
                "fp_by_case": {c: f"{sum(bool(m['e2_fires']) for m in ref_allow if m['intent_case'] == c)}/"
                                  f"{sum(1 for m in ref_allow if m['intent_case'] == c)}" for c in (3, 5, 6)},
                "hit_on_reference_CLARIFY": f"{sum(bool(m['e2_fires']) for m in premise)}/{len(premise)}",
                "miss_on_reference_CLARIFY": f"{sum(not m['e2_fires'] for m in premise)}/{len(premise)}",
                "fired_on_reference_DENY(redundant)": f"{sum(bool(m['e2_fires']) for m in deny)}/{len(deny)}"}
        for a in arms:
            chg = Counter(m["reference_verdict"] for m in M if E2CODE in (m["arms"][a].get("codes") or []))
            correct = sum((m["arms"][a]["decision"] == m["reference_verdict"]) for m in M)
            summ[a] = {"final_E2_code_by_reference": dict(chg), "final_equals_reference": f"{correct}/{len(M)}",
                       "allow_on_reference_CLARIFY": sum(m["arms"][a]["decision"] == "ALLOW" for m in premise),
                       "allow_on_reference_ALLOW": f"{sum(m['arms'][a]['decision'] == 'ALLOW' for m in ref_allow)}/{len(ref_allow)}"}
        out[tag] = {"summary": summ, "cells": cells}
    return out


def parity():
    eps = {e["episode_id"]: e for e in jl(V4 / "episodes.jsonl")}
    mg = {g["challenge_id"]: g for g in jl(V4 / "matched_stockout_gold.jsonl")}
    tx = jl(V4 / "transactions.jsonl")
    mx = jl(V4 / "matched_stockout.jsonl")

    def feats(e):
        d = e["dialogue"]
        return {"platform_turn": any(t["role"] == "tool" and t.get("source") == "platform" for t in d),
                "platform_stock0": any(t["role"] == "tool" and t.get("source") == "platform" and t.get("stock") == 0 for t in d),
                "seller_turn": any(t["role"] == "tool" and t.get("source") == "seller" for t in d),
                "other_tool_turn": any(t["role"] == "tool" and t.get("source") not in ("platform", "seller") for t in d),
                "catalog_stock0": any(c.get("stock") == 0 for c in e["catalog"]),
                "listing_text": any(c.get("listing_text") for c in e["catalog"]),
                "last_turn_role": d[-1]["role"] if d else None}
    res = {"transactions": dict(Counter(k for t in tx for k, v in feats(eps[t["episode_id"]]).items() if v is True)),
           "n_transactions": len(tx), "matched": {}}
    by = defaultdict(Counter)
    for m in mx:
        g = mg[m["challenge_id"]]
        f = feats(eps[m["episode_id"]])
        key = f"case{g['intent_case']}|{g['reference_verdict']}|{g['evidence_status']}"
        by[key]["n"] += 1
        for k, v in f.items():
            if v is True:
                by[key][k] += 1
    res["matched"] = {k: dict(v) for k, v in sorted(by.items())}
    res["transaction_fields"] = sorted(tx[0].keys())
    return res


def plain_m2_rows(rows, eps, txs, tg, matched_rows, mtx, mg):
    """PLAIN+M2 on v4 dev rows that carry plain_state; matched challenges reuse the plain_state of their episode."""
    plain = {r["episode_id"]: r["plain_state"] for r in rows if r.get("plain_state") is not None}
    out = []

    def decide(ep, tx, gold, st):
        case = X.build_case(ep, tx, gold)
        env = A.Env(case)
        mb = A.ledger_to_mandate(A.raw_ctx([{"seq": 0, "state": st}]), case.reg, case.seller, f"m-{case.episode_id}", 1, env.session)
        d, c = env.full_gate(mb)
        rec = verdict.integrated(d, c, False)
        cc = rec
        if rec == "ALLOW" and A.unverified(mb.primary, case) and case.t_kind == "consent_request":
            cc = "CLARIFY"
        return rec, cc, c
    for r in rows:
        st = r.get("plain_state")
        if st is None:
            continue
        rec, cc, c = decide(eps[r["episode_id"]], txs[r["transaction_id"]], tg.get(r["transaction_id"]) or {}, st)
        out.append({"kind": "tx", "id": r["transaction_id"], "episode_id": r["episode_id"], "type": r["transaction_type"],
                    "PLAIN_M2_record": rec, "PLAIN_M2_consent_clarify": cc, "codes": c,
                    "B2": r["arms"]["B2"]["decision"], "B3": r["arms"]["B3"]["decision"]})
    for m in matched_rows:
        st = plain.get(m["episode_id"])
        if st is None:
            continue
        rec, cc, c = decide(eps[m["episode_id"]], mtx[m["challenge_id"]], {}, st)
        out.append({"kind": "matched", "id": m["challenge_id"], "episode_id": m["episode_id"], "case": m["intent_case"],
                    "reference": m["reference_verdict"], "PLAIN_M2_record": rec, "PLAIN_M2_consent_clarify": cc, "codes": c,
                    "B2": m["arms"]["B2"]["decision"], "B3": m["arms"]["B3"]["decision"], "e2_fires": m["e2_fires"]})
    return out


def table(rows, pre, m1g):
    t = defaultdict(lambda: defaultdict(Counter))
    for r in rows:
        key = r["type"] if r["kind"] == "tx" else f"matched case{r['case']} ({r['reference']})"
        for arm in ("PLAIN_M2_record", "PLAIN_M2_consent_clarify", "B2", "B3"):
            t[key][arm][r[arm]] += 1
        p = pre.get(r["id"])
        if p:
            t[key]["PRECHECK"][p] += 1
        g = m1g.get(r["id"])
        if g:
            for arm in ("B2", "B3"):
                t[key][f"{arm}_frozen_m1g"][g[arm]] += 1
    return {k: {a: dict(c) for a, c in v.items()} for k, v in sorted(t.items())}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tags = ["A", "B"] + [t for t in ("A_m1g", "B_m1g") if (RES / f"rows_v4_dev_{t}_matched.jsonl").exists()]
    e2 = e2_analysis(tags)
    (OUT / "e2.json").write_text(json.dumps(e2, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    par = parity()
    (OUT / "parity.json").write_text(json.dumps(par, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    eps = {e["episode_id"]: e for e in jl(V4 / "episodes.jsonl")}
    txs = {t["transaction_id"]: t for t in jl(V4 / "transactions.jsonl")}
    tg = {g["transaction_id"]: g for g in jl(V4 / "transaction_gold.jsonl")}
    mtx = {m["challenge_id"]: m for m in jl(V4 / "matched_stockout.jsonl")}
    mg = {g["challenge_id"]: g for g in jl(V4 / "matched_stockout_gold.jsonl")}
    res = {"note": "exploratory arm PLAIN+M2 (not pre-registered); zero model calls", "m1g_rows_available": []}
    for cond in ("A", "B"):
        rows = jl(RES / f"rows_v4_dev_{cond}.jsonl")
        mrows = jl(RES / f"rows_v4_dev_{cond}_matched.jsonl")
        pm = plain_m2_rows(rows, eps, txs, tg, mrows, mtx, mg)
        (OUT / f"plain_m2_rows_{cond}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in pm),
                                                         encoding="utf-8", newline="\n")
        pre_file = RES / ("baselines_v4_dev.jsonl" if cond == "A" else "baselines_v4_dev_B.jsonl")
        pre = {b["id"]: b["precheck"] for b in jl(pre_file)}
        m1g = {}
        for suf in ("", "_matched"):
            for r in jl(RES / f"rows_v4_dev_{cond}_m1g{suf}.jsonl"):
                m1g[r.get("transaction_id") or r.get("challenge_id")] = {a: r["arms"][a]["decision"] for a in ("B2", "B3")}
        if m1g:
            res["m1g_rows_available"].append(cond)
        fr = [x for x in pm if x["kind"] == "tx"]
        follows = {g["transaction_id"] for g in tg.values() if g.get("follows_rejected_proposal")}
        res[cond] = {"precheck_file": pre_file.name if pre else None, "n_rows": len(pm), "table": table(pm, pre, m1g),
                     "follows_rejected_ALLOW": {arm: sum(1 for x in fr if x["id"] in follows and x[arm] == "ALLOW")
                                                for arm in ("PLAIN_M2_record", "PLAIN_M2_consent_clarify", "B2", "B3")},
                     "n_follows_rejected": sum(1 for x in fr if x["id"] in follows)}
        if pre:
            res[cond]["follows_rejected_ALLOW"]["PRECHECK"] = sum(1 for x in fr if x["id"] in follows and pre.get(x["id"]) == "ALLOW")
    if "--validation" in sys.argv:
        res["validation"] = validation()
    (OUT / "plain_m2_v4dev.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"e2": {k: v["summary"] for k, v in e2.items()}, "plain": {c: res.get(c, {}).get("table") for c in ("A", "B")},
                      "follows": {c: res.get(c, {}).get("follows_rejected_ALLOW") for c in ("A", "B")},
                      "validation": res.get("validation")}, indent=1, ensure_ascii=False))


def validation():
    """PLAIN+M2 on the validation development rows (P2 plain_state, extracted before t), groups as dev_eval."""
    import env as E
    dev = ROOT / "results" / "integrated_dev_20261126"
    ext = {}
    for s in ("V1", "V3", "V2"):
        for x in jl(dev / f"extract_{s}.jsonl"):
            ext[x["episode_id"]] = x
    ref_tag = "frozen_m1g" if (dev / "dev_rows_frozen_m1g.jsonl").exists() else "arms2"
    ref = {r["episode_id"]: r for r in jl(dev / f"dev_rows_{ref_tag}.jsonl")}
    cases = E.build_cases(set(ref))
    tab = defaultdict(Counter)
    for e, r in ref.items():
        c = cases[e]
        env = A.Env(c)
        mb = A.ledger_to_mandate(A.raw_ctx([{"seq": 0, "state": ext[e]["plain_state"]}]), c.reg, c.seller, f"m-{e}", 1, env.session)
        d, codes = env.full_gate(mb)
        rec = verdict.integrated(d, codes, False)
        cc = "CLARIFY" if (rec == "ALLOW" and A.unverified(mb.primary, c) and c.t_kind == "consent_request") else rec
        grp = "pay_viol" if r["pay_viol"] else ("legit" if r["outcome"] in ("RIGHT", "RIGHT_BY_LUCK") else "other_wrong")
        for arm, dec in (("PLAIN_M2_record", rec), ("PLAIN_M2_consent_clarify", cc), ("B2", r["arms"]["B2"]["decision"]),
                         ("B3", r["arms"]["B3"]["decision"]), ("AV2", r["arms"]["AV2"]["decision"])):
            tab[(grp, arm)][dec] += 1
    return {"reference_rows": f"dev_rows_{ref_tag}.jsonl", "table": {f"{g}|{a}": dict(v) for (g, a), v in sorted(tab.items())}}


if __name__ == "__main__":
    main()
