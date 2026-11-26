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
OURS_TO_FIELD = {"MAX_TOTAL": "Price", "QUANTITY": "Quantity", "BUNDLE_MEMBER_MISSING": "Quantity",
                 "SELECTED_MISSING": "Quantity", "ITEM": "Quantity", "BRAND": "Brand", "BRAND_EXCLUDED": "Brand",
                 "FULFILLMENT": "Fulfillment", "DEADLINE": "Deadline"}


def main(split="dev"):
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
        lines = [dataclasses.replace(case.catalog[k], quantity=q) for k, q in case.cart]
        viol = m.primary.violations(lines)
        cv, unk_c = checkout_violations(m.primary, case.checkout_facts)
        unk = m.primary.unknowns(lines)
        ours = {OURS_TO_FIELD.get(v.split(":")[0]) for v in viol + cv} - {None}
        unknown_fields = {u.split(":")[1] for u in unk} | set(unk_c)
        for f in sorted(theirs | ours | {"Stock", "Attribute"} & theirs):
            per_field[(f, "both" if f in theirs and f in ours else ("reference_only" if f in theirs else "ours_only"))] += 1
        rows.append({"transaction_id": tx["transaction_id"], "theirs": sorted(theirs), "ours": sorted(ours),
                     "ours_unknown": sorted(unknown_fields), "expected": (tg.get(tx["transaction_id"]) or {}).get("expected_checkout")})
    agree_any = sum(1 for r in rows if bool(r["theirs"]) == bool(r["ours"]))
    fields = sorted({f for f, _ in per_field})
    res = {"split": split, "transactions": len(rows), "agree_on_any_violation": agree_any,
           "per_field": {f: {k: per_field[(f, k)] for k in ("both", "reference_only", "ours_only")} for f in fields}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"cart_compare_{split}.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
    (OUT / f"cart_compare_rows_{split}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n")
    md = [f"# v4 {split}: 참조 cart_reasons() 대 우리 M2 범위 검사 (둘 다 정답 effective_state 기준, 모델 호출 0)", "",
          f"- 거래 {len(rows)}건. '위반 있음/없음' 일치: {agree_any}/{len(rows)}.", "",
          "| 필드 | 둘 다 위반 | 참조만 위반 | 우리만 위반 |", "|---|---:|---:|---:|"]
    for f in fields:
        d = res["per_field"][f]
        md.append(f"| {f} | {d['both']} | {d['reference_only']} | {d['ours_only']} |")
    (OUT / f"CART_COMPARE_{split}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
