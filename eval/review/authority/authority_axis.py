"""Review check (2026-11-27, model-free, system code untouched): the v4 authority axis and the reuse tests.

A  Current decisions on the v4 dev authority violations (authority_only + both), per arm, read from the existing rows
   (P4 condition A = before the freeze, main M1 rules v2; plus the frozen M1-G rows and the LLM baselines if present),
   and whether each authority_only transaction gets the SAME decision as a normal transaction of the same episode with
   an identical checkout (= the gate never sees the authority fields).
B  EXPLORATORY feed (labelled; mapping assumptions below): the unmodified cdv/gate.py::authorize is given the v4
   payment_request / payment_grant fields through inputs it already has:
     grant_id -> Mandate.mandate_id = grant.grant_id; the context record C_R names request.grant_id
     payer    -> the mandate is signed by grant.payer's key; the gate verifies with request.payer's public key
     payee    -> the cart lines being paid are keyed (request.payee, sku); the capture holds the store's offers
     expired  -> no mandate field exists (Mandate has no expiry); nothing can be mapped
   Scope = empty ScopeV2 (context conditions switched off) so only the authority mapping can change the decision.
   Each transaction is run twice: 'control' (request fields replaced by the grant's) and 'mapped' (real fields).
C  Stale-authority reuse on the 72 episodes of eval/v4check/stale_version.py: v1 (initial_state) vs v2
   (effective_state), both signed. For every transaction of those episodes: decision under v2 (current), under v1
   with version revocation (CDV), under v1 WITHOUT revocation (what reuse of the old authority would permit), and AV0.
Output: results/review_20261127/authority/authority_axis.json, AUTHORITY_AXIS.md
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import arms as A  # noqa: E402
import run_ext as X  # noqa: E402
from cdv.canon import new_signing_key, public_of  # noqa: E402
from cdv.gate import Request, authorize, combined_hash, context_record  # noqa: E402
from cdv.mandate import Mandate, VersionRegistry  # noqa: E402
from cdv.v2.integrate import ledger_to_mandate  # noqa: E402
from cdv.v2.scope import ScopeV2  # noqa: E402

V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4/dev")
RES = ROOT / "results" / "extdata_20261126"
OUT = ROOT / "results" / "review_20261127" / "authority"
_KEYS: dict = {}


def sk(name):
    if name not in _KEYS:
        _KEYS[name] = new_signing_key()
    return _KEYS[name]


def reason(g):
    r = g.get("authority_reasons") or []
    return r[0] if r else "none"


def checkout_key(tx):
    return json.dumps(tx["checkout"], sort_keys=True)


def part_a(txs, tg):
    out = {}
    by_ep = defaultdict(list)
    for t in txs.values():
        by_ep[t["episode_id"]].append(t)
    files = {"P4_A_rules_v2(pre-freeze)": RES / "rows_v4_dev_A.jsonl", "R-v4g_A_M1-G(post-freeze)": RES / "rows_v4_dev_A_m1g.jsonl"}
    for label, f in files.items():
        if not f.exists():
            out[label] = "not present"
            continue
        rows = {r["transaction_id"]: r for r in X.jl(f)}
        res = {"n_rows": len(rows), "by_reason": {}, "pair_identical": {}}
        arms = list(next(iter(rows.values()))["arms"])
        for rs in ("payee", "expired", "payer", "grant_id"):
            R = [r for r in rows.values() if reason(tg[r["transaction_id"]]) == rs]
            res["by_reason"][rs] = {a: dict(Counter(r["arms"][a]["decision"] for r in R)) for a in arms} | {"n": len(R)}
        for typ, ctrl in (("authority_only", "normal"), ("both", "context_only")):
            same, total, nopair = Counter(), 0, 0
            for r in rows.values():
                if tg[r["transaction_id"]]["transaction_type"] != typ:
                    continue
                ck = checkout_key(txs[r["transaction_id"]])
                mates = [t for t in by_ep[r["episode_id"]] if tg[t["transaction_id"]]["transaction_type"] == ctrl
                         and checkout_key(t) == ck and t["transaction_id"] in rows]
                if not mates:
                    nopair += 1
                    continue
                total += 1
                m = rows[mates[0]["transaction_id"]]
                for a in arms:
                    same[a] += r["arms"][a]["decision"] == m["arms"][a]["decision"]
            res["pair_identical"][f"{typ} vs {ctrl}"] = {"paired": total, "no_identical_checkout_mate": nopair,
                                                         "same_decision_per_arm": dict(same)}
        out[label] = res
    bl = RES / "baselines_v4_dev.jsonl"
    if bl.exists():
        B = [b for b in X.jl(bl) if b["kind"] == "tx"]
        out["baselines(condition A)"] = {rs: {k: dict(Counter(b[k] for b in B if reason(tg[b["id"]]) == rs))
                                              for k in ("precheck", "summary")}
                                         for rs in ("payee", "expired", "payer", "grant_id", "none")}
        bid = {b["id"]: b for b in B}
        by_ep = defaultdict(list)
        for t in txs.values():
            by_ep[t["episode_id"]].append(t)
        same = Counter()
        n = 0
        for b in B:
            if tg[b["id"]]["transaction_type"] != "authority_only":
                continue
            ck = checkout_key(txs[b["id"]])
            mates = [t for t in by_ep[b["episode_id"]] if tg[t["transaction_id"]]["transaction_type"] == "normal"
                     and checkout_key(t) == ck and t["transaction_id"] in bid]
            if mates:
                n += 1
                for k in ("precheck", "summary"):
                    same[k] += b[k] == bid[mates[0]["transaction_id"]][k]
        out["baselines(condition A)"]["authority_only vs normal identical-checkout mate"] = {"paired": n, "same_decision": dict(same)}
        out["baselines(condition A)"]["authority_only decisions"] = {
            k: dict(Counter(b[k] for b in B if tg[b["id"]]["transaction_type"] == "authority_only")) for k in ("precheck", "summary")}
    return out


def gate_once(case, env, pr, g):
    m = Mandate(g["grant_id"], 1, ScopeV2(), session=env.session).signed(sk(g["payer"]))
    vr = VersionRegistry()
    vr.publish(g["grant_id"], 1)
    cart = [((pr["payee"], k[1]), q) for k, q in case.cart]
    c_r = dict(context_record(m, None, []), mandate_id=pr["grant_id"])
    req = Request(m, public_of(sk(pr["payer"])), vr, env.session, case.offers, case.catalog, cart, env.avip_r, c_r,
                  combined_hash(A.avip.record_hash(env.avip_r), c_r), env.evid, A.ISSUERS, A.NonceStore(), A.NOW)
    r = authorize(req)
    return r.decision, (r.codes[0] if r.codes else "")


def part_b(txs, tg, eps, keep):
    tab = defaultdict(Counter)
    for t in txs.values():
        if t["episode_id"] not in keep:
            continue
        gt = tg[t["transaction_id"]]
        case = X.build_case(eps[t["episode_id"]], t, gt)
        env = A.Env(case)
        g, pr = t["payment_grant"], t["payment_request"]
        ctrl = {**pr, "grant_id": g["grant_id"], "payer": g["payer"], "payee": g["payee"]}
        dc, cc = gate_once(case, env, ctrl, g)
        dm, cm = gate_once(case, env, pr, g)
        tab[reason(gt)][f"control {dc} {cc} -> mapped {dm} {cm}"] += 1
    return {k: dict(v) for k, v in tab.items()}


def part_c(txs, tg, eps, keep):
    eg = {g["episode_id"]: g for g in X.jl(V4 / "episode_gold.jsonl")}
    eps72 = sorted({t["episode_id"] for t in txs.values() if eg[t["episode_id"]].get("accepted_changes")
                    and tg[t["transaction_id"]]["transaction_type"] == "normal"})
    tab = defaultdict(Counter)
    for e in eps72:
        ep, g = eps[e], eg[e]
        cat = {x["sku"]: x for x in ep["catalog"]}
        for t in [t for t in txs.values() if t["episode_id"] == e]:
            gt = tg[t["transaction_id"]]
            if gt["transaction_type"] not in ("normal", "context_only"):
                continue
            case = X.build_case(ep, t, gt)
            env = A.Env(case)
            mid = f"m-{case.episode_id}"
            m1 = ledger_to_mandate(X.gold_ctx({"effective_state": g["initial_state"]}, cat), case.reg, case.seller, mid, 1, env.session).signed(A.USER_SK)
            m2 = ledger_to_mandate(X.gold_ctx({"effective_state": g["effective_state"]}, cat), case.reg, case.seller, mid, 2, env.session).signed(A.USER_SK)

            def run(m, vr):
                c_r = context_record(m, None, [])
                r = authorize(Request(m, A.USER_PK, vr, env.session, case.offers, case.catalog, case.cart, env.avip_r, c_r,
                                      combined_hash(A.avip.record_hash(env.avip_r), c_r), env.evid, A.ISSUERS, A.NonceStore(), A.NOW))
                return r.decision
            vr_cdv = VersionRegistry()
            vr_cdv.publish(mid, 1)
            vr_cdv.publish(mid, 2)
            d_v1_cdv = run(m1, vr_cdv)                       # raw gate with revocation: version check first
            # full integrated gate (consent-time checks, fee total, E2) WITHOUT revocation: what each authority permits
            u1 = ledger_to_mandate(X.gold_ctx({"effective_state": g["initial_state"]}, cat), case.reg, case.seller, mid, 1, env.session)
            u2 = ledger_to_mandate(X.gold_ctx({"effective_state": g["effective_state"]}, cat), case.reg, case.seller, mid, 2, env.session)
            d_v2 = env.full_gate(u2)[0]
            d_v1_norev = env.full_gate(u1)[0]
            d_av0 = A.avip_simple(env, None)[0]
            tab[gt["transaction_type"]][f"v2 current (full gate) {d_v2} | v1 under CDV {d_v1_cdv} | v1 if no revocation (full gate) {d_v1_norev} | AV0 {d_av0}"] += 1
    return {"episodes": len(eps72), "by_type": {k: dict(v) for k, v in tab.items()}}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    eps = {e["episode_id"]: e for e in X.jl(V4 / "episodes.jsonl")}
    txs = {t["transaction_id"]: t for t in X.jl(V4 / "transactions.jsonl")}
    tg = {g["transaction_id"]: g for g in X.jl(V4 / "transaction_gold.jsonl")}
    excl = set(json.loads((RES / "exclusion_v4_dev.json").read_text(encoding="utf-8"))["excluded_episodes"])
    keep = set(eps) - excl
    txs = {k: t for k, t in txs.items() if t["episode_id"] in keep}
    res = {"A_current_decisions": part_a(txs, tg), "B_exploratory_feed": part_b(txs, tg, eps, keep),
           "C_stale_reuse": part_c(txs, tg, eps, keep),
           "n_transactions": len(txs), "authority_reasons": dict(Counter(reason(tg[k]) for k in txs))}
    (OUT / "authority_axis.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
