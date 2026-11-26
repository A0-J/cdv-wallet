"""Prior-version mandate reuse test (v4 dev, no model calls).

For every dev episode with an accepted change: mandate v1 from initial_state, v2 from effective_state (same mandate id),
both signed by the user key; the wallet publishes v1 then v2 (v1 is revoked). A payment request (the episode's
expected-allow transaction) is attempted with v1 and with v2 through cdv/gate.py::authorize.
Expected: v1 -> DENY STALE_VERSION in every case; v2 -> the normal gate decision.
Output: results/v4check_20261126/stale_version_dev.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import arms as A  # noqa: E402
import run_ext as X  # noqa: E402
from cdv.gate import Request, authorize, combined_hash, context_record  # noqa: E402
from cdv.mandate import VersionRegistry  # noqa: E402
from cdv.v2.integrate import ledger_to_mandate  # noqa: E402

V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4")


def main():
    eps = {e["episode_id"]: e for e in X.jl(V4 / "dev" / "episodes.jsonl")}
    eg = {g["episode_id"]: g for g in X.jl(V4 / "dev" / "episode_gold.jsonl")}
    tg = {g["transaction_id"]: g for g in X.jl(V4 / "dev" / "transaction_gold.jsonl")}
    c = Counter()
    for tx in X.jl(V4 / "dev" / "transactions.jsonl"):
        g, gt = eg[tx["episode_id"]], tg.get(tx["transaction_id"]) or {}
        if not g.get("accepted_changes") or gt.get("transaction_type") != "normal":
            continue
        ep = eps[tx["episode_id"]]
        cat = {x["sku"]: x for x in ep["catalog"]}
        case = X.build_case(ep, tx, gt)
        env = A.Env(case)
        mid = f"m-{case.episode_id}"
        m1 = ledger_to_mandate(X.gold_ctx({"effective_state": g["initial_state"]}, cat), case.reg, case.seller, mid, 1, env.session).signed(A.USER_SK)
        m2 = ledger_to_mandate(X.gold_ctx({"effective_state": g["effective_state"]}, cat), case.reg, case.seller, mid, 2, env.session).signed(A.USER_SK)
        vr = VersionRegistry()
        vr.publish(mid, 1)
        vr.publish(mid, 2)                       # v1 revoked
        for name, m in (("v1_stale", m1), ("v2_current", m2)):
            c_r = context_record(m, None, [])
            res = authorize(Request(m, A.USER_PK, vr, env.session, case.offers, case.catalog, case.cart, env.avip_r, c_r,
                                    combined_hash(A.avip.record_hash(env.avip_r), c_r), env.evid, A.ISSUERS, A.NonceStore(), A.NOW))
            c[(name, res.decision, res.codes[0] if res.codes else "")] += 1
    out = {"episodes_with_accepted_change_normal_tx": sum(v for (n, _, _), v in c.items() if n == "v1_stale"),
           "results": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in sorted(c.items())}}
    (ROOT / "results" / "v4check_20261126" / "stale_version_dev.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
