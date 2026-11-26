"""Integrated-evaluation feasibility on CartTrace (no model calls, no rule changes).

Question: does one CartTrace journey carry what M1 -> Ledger -> Signed Mandate -> M2 needs at runtime,
without the hidden spec?  Measured on the validation split only.
  - final cart lines (variant_id, unit_price, quantity)            -> payment request
  - cart variant ids present in catalog tool results               -> A-VIP capture / NOT_CAPTURED / chosen
  - structured brand / attributes / availability in tool results   -> trusted catalog facts for Scope
  - number of merchants per journey                                -> cross-seller claims possible?
  - stockout faults visible as availability=false in tool results  -> platform evidence for substitution clauses
  - payment protocol family                                        -> native mandate exists (AP2) or simulated
Output: results/integrated_design_20261126/feasibility.json
Usage:  .venv/Scripts/python.exe eval/integrated/feasibility.py
"""
from __future__ import annotations

import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(r"C:/ct/kit/dataset/data")
OUT = ROOT / "results" / "integrated_design_20261126"
CATALOG_TOOLS = {"search_catalog", "lookup_catalog", "get_product", "search_products", "compare_products", "send_intent_mandate"}


def dec(s):
    try:
        o = json.loads(s or "null")
        while isinstance(o, str):
            o = json.loads(o)
        return o
    except (json.JSONDecodeError, TypeError):
        return None


def products(o, out):
    if isinstance(o, dict):
        if ("id" in o or "sku" in o) and ("title" in o or "metadata" in o) and ("price" in o or "price_range" in o or "variants" in o):
            out.append(o)
        for v in o.values():
            products(v, out)
    elif isinstance(o, list):
        for v in o:
            products(v, out)


def family(tools):
    if tools & {"create_checkout_mandate", "sign_mandates_on_user_device"}:
        return "AP2 (native mandates)"
    if "create_checkout_session" in tools:
        return "ACP"
    if "request_payment" in tools:
        return "MPP/402"
    if tools & {"create_checkout", "start_checkout"}:
        return "UCP/checkout"
    return "cart handover only"


def main(split="validation"):
    msgs = {}
    for f in glob.glob(str(DATA / "messages" / "*" / f"{split}-*.parquet")):
        for r in pq.read_table(f, columns=["episode_id", "final_cart", "kind", "sub_kind", "outcome_class", "hidden_spec"]).to_pylist():
            msgs[r["episode_id"]] = r
    T = defaultdict(list)
    for f in glob.glob(str(DATA / "turns" / f"{split}-*.parquet")):
        for x in pq.read_table(f, columns=["episode_id", "seq", "actor", "kind", "tool", "result"]).to_pylist():
            T[x["episode_id"]].append(x)
    c, fam, merch = Counter(), Counter(), Counter()
    kinds = Counter((m["kind"], m["sub_kind"], m["outcome_class"]) for m in msgs.values())
    fault_kinds = Counter(f.get("kind") for m in msgs.values() for f in (json.loads(m["hidden_spec"]).get("faults") or []))
    for e, ts in T.items():
        m = msgs.get(e)
        if not m or m["kind"] != "baseline":
            continue
        c["journeys"] += 1
        fam[family({x["tool"] for x in ts if x["kind"] == "tool_call"})] += 1
        ids, unavailable, merchants, brand, attrs = set(), set(), set(), False, False
        for x in ts:
            if x["kind"] != "tool_result":
                continue
            merchants |= set(re.findall(r"ct-\d+\.example", x["result"] or ""))
            if x["tool"] not in CATALOG_TOOLS:
                continue
            ps = []
            products(dec(x["result"]), ps)
            for p in ps:
                ids.add(str(p.get("id") or p.get("sku")))
                md = p.get("metadata") or {}
                brand |= bool(md.get("brand") or p.get("brand"))
                attrs |= bool(md.get("attributes"))
                for v in p.get("variants") or []:
                    if isinstance(v, dict):
                        ids.add(str(v.get("id")))
                        if (v.get("availability") or {}).get("available") is False:
                            unavailable.add(str(v.get("id")))
                if p.get("available") is False:
                    unavailable.add(str(p.get("sku") or p.get("id")))
        merch[str(min(len(merchants), 2)) + (" +" if len(merchants) >= 2 else "")] += 1
        c["brand_metadata_in_results"] += brand
        c["attributes_in_results"] += attrs
        faults = [f for f in (json.loads(m["hidden_spec"]).get("faults") or []) if f.get("kind") == "stockout"]
        if faults:
            c["stockout_journeys"] += 1
            c["stockout_variant_shown_unavailable"] += any(str(f.get("variant")) in unavailable for f in faults)
        cart = dec(m["final_cart"]) or {}
        lines = cart.get("lines") or []
        if not lines:
            c["no_final_cart"] += 1
            continue
        c["with_final_cart"] += 1
        vids = [str(l.get("variant_id")) for l in lines]
        c["cart_lines_all_in_catalog_results"] += all(v in ids or any(i.endswith("/" + v) or i.endswith(v) for i in ids) for v in vids)
        c["cart_lines_have_price_and_qty"] += all(l.get("unit_price") is not None and l.get("quantity") for l in lines)
    res = {"split": split, "note": "no model calls; hidden spec used only to count stockout faults (scoring side)",
           "counts": dict(c), "protocol_family": dict(fam), "merchants_per_journey": dict(merch),
           "all_kinds_subkinds_outcomes": {" / ".join(map(str, k)): v for k, v in kinds.most_common()},
           "fault_kinds_all_episodes": dict(fault_kinds)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "feasibility.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
