"""Review item 5: natural extractor errors vs injected error types on v4 dev, and the cost of an injection whose prior is
the real extractor output (no model calls; request hashes are only computed and looked up in existing ledgers).

(a) Natural errors: per episode (430 kept), the FnCTOD state before t (rows_v4_dev_{A,B}.jsonl, condition A = shopper and
    agent turns only, B = seller turns also given to the extractor) as entries (arms.raw_ctx) vs the gold effective state
    as entries (run_ext.gold_ctx). Entry ids compared: budget, qty, brand_in, brand_out, bundle, deadline, ful, sub.
    Kinds: missed (gold has it, extractor not), extra (extractor has it, gold not), wrong (both, different value).
    Cause tags: 'follows invalid/clarify proposal' (value equals a candidate operation labelled reject or clarify on that
    entry, or a REVOKE so labelled for a missed entry), 'stale' (equals the initial state although gold changed it),
    'value in seller text' (number/brand appears in a seller tool turn), else 'other'.
    Comparison limits: qty = total count (extractor keeps one number); bundle compared by item count only.
(b) Injected errors: candidate operations labelled reject / clarify, by cause (proposed_invalid_operations.cause or the
    clarify subtype) and by effect kind relative to gold (REVOKE -> missed-like, sets an entry gold lacks -> extra-like,
    else wrong-like). Also: how often the extractor's final state naturally reflects each reject-labelled proposal.
(c) Cost of the extractor-prior injection: request sha256 exactly as cdv/extract.py OpenAIResponses builds it, looked up
    in the M1-G ledgers (prompt_v2 run1/run2 of the injection; ledger_m1g_v4.jsonl of the natural path).
Output: results/review_20261127/m1g_det/natural_vs_injected.json (tables are written up in REPORT.md)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata", "eval/v4check"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import arms as A  # noqa: E402
import inject as I  # noqa: E402
import run_ext as X  # noqa: E402
from cdv.v2 import m1g  # noqa: E402
from cdv.v2.m1g_path import describe_entry  # noqa: E402

V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4")
OUT = ROOT / "results" / "review_20261127" / "m1g_det"
IDS = ("budget", "qty", "brand_in", "brand_out", "bundle", "deadline", "ful", "sub")
FIELD_OF = {"budget": "Price", "qty": "Quantity", "brand_in": "Brand", "brand_out": "Brand", "bundle": "Bundle",
            "deadline": "Deadline", "ful": "Fulfillment", "sub": "Substitution"}


def norm(eid, e):
    if e is None:
        return None
    v = e.value
    if eid == "budget":
        return round(float(v), 2)
    if eid in ("qty", "deadline"):
        return int(v)
    if eid in ("brand_in", "brand_out"):
        return tuple(sorted(str(x).strip().lower() for x in v))
    if eid == "bundle":
        return len(v)
    if eid == "sub":
        return "present"
    return str(v)


def op_entries(op, cat):
    """candidate operation -> {entry id: normalised value or None (removed)}."""
    out = {}
    try:
        for eid, e in I.entries_from(op["field"], None if op["operation"] == "REVOKE" else op.get("value"), cat):
            if eid in IDS:
                out[eid] = norm(eid, e)
    except Exception:  # noqa: BLE001 - unsupported shapes (Attribute, Product) give no entry
        pass
    return out


def body_sha(system, user, model="gpt-6-luna", effort="low", max_out=2000):
    body = json.dumps({"model": model, "input": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                       "reasoning": {"effort": effort}, "max_output_tokens": max_out}).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def ledger_shas(p):
    p = Path(p)
    if not p.exists():
        return set(), 0.0, 0
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l]
    ok = [r for r in rows if r.get("request_sha256") and not r.get("error") and r.get("status") == "completed"]
    return {r["request_sha256"] for r in ok}, sum(r.get("cost_usd") or 0 for r in ok), len(ok)


def main():
    eps = {e["episode_id"]: e for e in X.jl(V4 / "dev" / "episodes.jsonl")}
    eg = {g["episode_id"]: g for g in X.jl(V4 / "dev" / "episode_gold.jsonl")}
    tg = {g["transaction_id"]: g for g in X.jl(V4 / "dev" / "transaction_gold.jsonl")}
    txs = {t["transaction_id"]: t for t in X.jl(V4 / "dev" / "transactions.jsonl")}
    excl = set(json.loads((ROOT / "results" / "extdata_20261126" / "exclusion_v4_dev.json").read_text(encoding="utf-8"))["excluded_episodes"])
    rows = {}
    for cond in ("A", "B"):
        rows[cond] = {}
        for l in (ROOT / "results" / "extdata_20261126" / f"rows_v4_dev_{cond}.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(l)
            rows[cond].setdefault(r["episode_id"], r)
    nat = {c: Counter() for c in ("A", "B")}
    nat_cause = {c: Counter() for c in ("A", "B")}
    adopt = {c: Counter() for c in ("A", "B")}
    adopt_n = Counter()
    inj = Counter()
    inj_cause = Counter()
    ep_err = {c: 0 for c in ("A", "B")}
    for e, ep in eps.items():
        if e in excl:
            continue
        g = eg[e]
        cat = {c["sku"]: c for c in ep["catalog"]}
        gold = {k: norm(k, v) for k, v in X.gold_ctx(g, cat).entries.items() if k in IDS}
        init = {k: norm(k, v) for k, v in X.gold_ctx({"effective_state": g["initial_state"]}, cat).entries.items() if k in IDS}
        seller_txt = " ".join(t["text"] for t in ep["dialogue"] if t["role"] == "tool" and t.get("source") == "seller").lower()
        labels = g["operation_labels"]
        pio = {(o["field"], o["operation"], json.dumps(o.get("value"), sort_keys=True)): o["cause"] for o in g["proposed_invalid_operations"]}
        bad_ops = []
        for op in ep["candidate_operations"]:
            lab = labels[op["op_id"]]
            if lab not in ("reject", "clarify"):
                continue
            cause = pio.get((op["field"], op["operation"], json.dumps(op.get("value"), sort_keys=True))) if lab == "reject" else f"clarify:{g['subtype']}"
            cause = cause or ("reject:" + g["subtype"])
            oe = op_entries(op, cat)
            bad_ops.append((op, lab, cause, oe))
            for eid, val in oe.items():
                kind = "missed-like (removes)" if val is None else ("extra-like (adds)" if eid not in gold else "wrong-like (changes)")
                inj[(lab, kind, eid)] += 1
                inj_cause[(lab, cause, eid)] += 1
            if not oe:
                inj[(lab, "no entry (unsupported field)", op["field"])] += 1
        tx = next(t for t in txs.values() if t["episode_id"] == e)
        case = X.build_case(ep, tx, tg.get(tx["transaction_id"]) or {})
        for cond in ("A", "B"):
            r = rows[cond].get(e)
            if not r:
                continue
            st = sorted([{"seq": int(s["turn_id"][1:]), "state": s["state"]} for s in r["fnctod_states"] if int(s["turn_id"][1:]) < case.t],
                        key=lambda s: s["seq"])
            ext = {k: norm(k, v) for k, v in A.raw_ctx(st).entries.items() if k in IDS}
            any_err = False
            for eid in IDS:
                gv, xv = gold.get(eid), ext.get(eid)
                if gv == xv:
                    continue
                any_err = True
                kind = "missed" if xv is None else ("extra" if gv is None else "wrong")
                nat[cond][(kind, eid)] += 1
                tags = []
                for op, lab, cause, oe in bad_ops:
                    # a removed entry counts as following a proposal only when that proposal is a REVOKE (other ops
                    # also yield None for sub-entries they do not set, e.g. brand_out of an include-only Brand op)
                    if eid in oe and oe[eid] == xv and (xv is not None or op["operation"] == "REVOKE"):
                        tags.append(f"follows {lab} proposal ({cause})")
                if xv is not None and init.get(eid) == xv and gv != xv:
                    tags.append("stale (initial value kept)")
                if xv is None and init.get(eid) is None and gv is not None:
                    tags.append("never extracted")
                if xv is not None and eid in ("budget", "deadline", "qty") and re.search(rf"\b{re.escape(str(int(xv)) if isinstance(xv, (int, float)) and float(xv).is_integer() else str(xv))}\b", seller_txt):
                    tags.append("value in seller text")
                if xv is not None and eid in ("brand_in", "brand_out") and any(b and b in seller_txt for b in xv):
                    tags.append("value in seller text")
                nat_cause[cond][(kind, tags[0] if tags else "other")] += 1
            ep_err[cond] += any_err
            for op, lab, cause, oe in bad_ops:
                if lab != "reject" or not oe:
                    continue
                if cond == "A":
                    adopt_n[cause] += 1
                if all(ext.get(eid) == val for eid, val in oe.items()) and any(gold.get(eid) != val for eid, val in oe.items()):
                    adopt[cond][cause] += 1
    # (c) cache lookups
    v2_1, cost1, n1 = ledger_shas(ROOT / "results" / "m1g_20261126" / "prompt_v2" / "ledger_run1.jsonl")
    v2_2, _, _ = ledger_shas(ROOT / "results" / "m1g_20261126" / "prompt_v2" / "ledger_run2.jsonl")
    nat_led, _, n_nat = ledger_shas(ROOT / "results" / "extdata_20261126" / "ledger_m1g_v4.jsonl")
    per_call = cost1 / max(1, n1)
    d1 = Counter()
    d2 = Counter()
    for e, ep in eps.items():
        if e in excl:
            continue
        cat = {c["sku"]: c for c in ep["catalog"]}
        by = {t["turn_id"]: t for t in ep["dialogue"]}
        for op in ep["candidate_operations"]:
            t = by.get(op["evidence_turn_id"]) or {}
            if t.get("role") != "user":
                d1["non-user cited (no call)"] += 1
                continue
            s = body_sha(m1g.SYSTEM, m1g.TEMPLATES["v2"].format(turn=t["text"], change=m1g.describe(op, cat)))
            d1["hit run1" if s in v2_1 else "miss run1"] += 1
            d1["hit run2" if s in v2_2 else "miss run2"] += 1
            try:
                ents = I.entries_from(op["field"], None if op["operation"] == "REVOKE" else op.get("value"), cat)
            except Exception:  # noqa: BLE001
                ents = []
            for eid, new in ents:
                if eid not in IDS and eid != "ptype":
                    continue
                old = new if new is not None else type("O", (), {"field": {"budget": "budget_max", "qty": "quantity", "bundle": "bundle_all",
                                                                          "deadline": "deadline_days", "ful": "fulfillment", "sub": "substitute",
                                                                          "ptype": "product_type"}.get(eid, eid)})()
                txt = describe_entry(None if new is not None else old, new)
                s2 = body_sha(m1g.SYSTEM, m1g.TEMPLATES["v2"].format(turn=t["text"], change=txt))
                d2["hit" if (s2 in nat_led or s2 in v2_1) else "miss"] += 1
    res = {"episodes": len([e for e in eps if e not in excl]),
           "episodes_with_any_natural_error": ep_err,
           "natural_errors": {c: {f"{k}|{i}": v for (k, i), v in sorted(nat[c].items())} for c in nat},
           "natural_error_causes": {c: {f"{k}|{t}": v for (k, t), v in sorted(nat_cause[c].items())} for c in nat_cause},
           "injected_ops_by_effect": {f"{l}|{k}|{i}": v for (l, k, i), v in sorted(inj.items())},
           "injected_ops_by_cause": {f"{l}|{c}|{i}": v for (l, c, i), v in sorted(inj_cause.items())},
           "reject_proposal_natural_adoption": {c: {k: f"{adopt[c][k]}/{adopt_n[k]}" for k in sorted(adopt_n)} for c in adopt},
           "design1_candidate_wording_cache": dict(d1),
           "design2_natural_wording_cache": dict(d2), "natural_ledger_completed_requests_at_read": n_nat,
           "observed_cost_per_m1g_call_usd": round(per_call, 8)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "natural_vs_injected.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
