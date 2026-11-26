"""v4: the dataset's reference cart_reasons() vs our M2 scope check, both on the GOLD effective state (no model calls).

Question: given the correct conditions, does our mandate scope (ScopeV2 + consent-point checkout check) flag the same
fields as v4's reference function? This measures M2's expressiveness, not M1. Run on dev only (rules are being frozen;
eval is not used to change anything).
v4 code is imported read-only for cart_reasons/required_lines/checkout_amount (module has no top-level side effects;
checked 2026-11-26). Output: results/v4check_20261126/cart_compare_dev.json, CART_COMPARE_dev.md
"""
from __future__ import annotations

import dataclasses
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4")
sys.path.append(str(V4))                     # appended: never shadows our modules
import build_dataset_v4 as B  # noqa: E402
import arms as A  # noqa: E402
import run_ext as X  # noqa: E402
from cdv.v2.scope import checkout_violations  # noqa: E402

OUT = ROOT / "results" / "v4check_20261126"
OURS_TO_FIELD = {"MAX_TOTAL": "Price", "MAX_TOTAL_WITH_FEES": "Price", "QUANTITY": "Quantity", "BUNDLE_MEMBER_MISSING": "Quantity",
                 "SELECTED_MISSING": "Quantity", "ITEM": "Quantity", "BRAND": "Brand", "BRAND_EXCLUDED": "Brand",
                 "FULFILLMENT": "Fulfillment", "DEADLINE": "Deadline"}


def main(split="dev", tag=""):
    eps = {e["episode_id"]: e for e in X.jl(V4 / split / "episodes.jsonl")}
    eg = {g["episode_id"]: g for g in X.jl(V4 / split / "episode_gold.jsonl")}
    tg = {g["transaction_id"]: g for g in X.jl(V4 / split / "transaction_gold.jsonl")}
    per_field = Counter()
    rows = []
    for tx in X.jl(V4 / split / "transactions.jsonl"):
        ep, g = eps[tx["episode_id"]], eg[tx["episode_id"]]
        st = g["effective_state"]
        cat = {c["sku"]: c for c in ep["catalog"]}
        theirs = set(B.cart_reasons(tx["checkout"], st, cat))
        case = X.build_case(ep, tx, tg.get(tx["transaction_id"]) or {})
        env = A.Env(case)
        m = A.ledger_to_mandate(X.gold_ctx(g, cat), case.reg, case.seller, "m", 1, env.session)
        d_gate, codes = env.full_gate(m)                 # the real gate: scope, clauses + platform evidence, payment total
        ours = {OURS_TO_FIELD.get(str(c).split(":")[0]) for c in codes} - {None} if d_gate == "DENY" else set()
        unknown_fields = {str(c).split(":")[1] for c in codes if str(c).startswith("UNKNOWN_ATTR:")}
        per_field[("_decision", d_gate)] += 1
        for f in sorted(theirs | ours):
            per_field[(f, "both" if f in theirs and f in ours else ("reference_only" if f in theirs else "ours_only"))] += 1
        rows.append({"transaction_id": tx["transaction_id"], "theirs": sorted(theirs), "ours": sorted(ours), "ours_decision": d_gate,
                     "ours_unknown": sorted(unknown_fields), "expected": (tg.get(tx["transaction_id"]) or {}).get("expected_checkout")})
    agree_any = sum(1 for r in rows if bool(r["theirs"]) == (r["ours_decision"] != "ALLOW"))
    fields = sorted({f for f, _ in per_field if f != "_decision"})
    res = {"split": split, "transactions": len(rows), "agree_on_any_violation": agree_any,
           "per_field": {f: {k: per_field[(f, k)] for k in ("both", "reference_only", "ours_only")} for f in fields}}
    OUT.mkdir(parents=True, exist_ok=True)
    sfx = f"_{tag}" if tag else ""
    assert not (OUT / f"cart_compare_{split}{sfx}.json").exists(), "refusing to overwrite"
    (OUT / f"cart_compare_{split}{sfx}.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
    (OUT / f"cart_compare_rows_{split}{sfx}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n")
    md = [f"# v4 {split}: 참조 cart_reasons() 대 우리 M2 범위 검사 (둘 다 정답 effective_state 기준, 모델 호출 0)", "",
          f"- 거래 {len(rows)}건. 우리 게이트 판정 분포: " + str({k: v for (f, k), v in per_field.items() if f == "_decision"}) +
          f". '참조 위반 있음' 대 '우리 판정이 ALLOW 아님' 일치: {agree_any}/{len(rows)}. 필드별 표는 DENY 사유만 센다.", "",
          "| 필드 | 둘 다 위반 | 참조만 위반 | 우리만 위반 |", "|---|---:|---:|---:|"]
    for f in fields:
        d = res["per_field"][f]
        md.append(f"| {f} | {d['both']} | {d['reference_only']} | {d['ours_only']} |")
    (OUT / f"CART_COMPARE_{split}{sfx}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev", sys.argv[2] if len(sys.argv) > 2 else "")
