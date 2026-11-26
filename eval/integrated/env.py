"""CartTrace journey -> IntegratedCase (runtime inputs only; scoring fields kept apart).

Input checks (stop, never skip): every requested episode must be found (messages and turns, across ALL
four splits), have shopper turns before the decision point t, a non-empty payment-request cart, and a
non-empty candidate registry. A mismatch between requested and built cases stops the run.
The decision point t is the single shared definition in eval/e_m1/recompute_truncated.py::decision_point.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "e_m1"))
sys.path.insert(0, str(ROOT / "eval" / "m1_v2"))
from cdv.m1 import UserTurn  # noqa: E402
from cdv.v2.candidates import Registry, build_registry, norm_id  # noqa: E402
from cdv.v2.scope import LineV2  # noqa: E402
from recompute_truncated import decision_point  # noqa: E402  (shared definition of t)

DATA = Path(r"C:/ct/kit/dataset/data")
SPLITS = ("train", "validation", "test_cross_store", "test_cross_template")


class InputError(SystemExit):
    pass


@dataclass
class IntegratedCase:
    episode_id: str
    split: str
    source: str                         # "original" | "generated:<id>"
    t: float
    t_kind: str
    user_turns: list                    # UserTurn, seq < t
    agent_turns: list                   # (seq, text), seq < t
    reg: Registry                       # candidates from tool results before t
    seller: str
    offers: list                        # A-VIP capture input
    catalog: dict                       # (seller, cart_id) -> LineV2 (structured fields; cart price = payment request)
    cart: list                          # [((seller, variant_id), quantity)]
    unavailable: list                   # (seller, variant_id) shown unavailable by the platform before t
    checkout_facts: dict = field(default_factory=dict)   # fulfillment / max delivery days from checkout state before t
    scoring: dict = field(default_factory=dict)   # hidden spec, outcome: NEVER passed to an arm


def load_rows(eids: set):
    eids = set(eids)
    msgs, turns = {}, {}
    mcols = ["episode_id", "hidden_spec", "outcome_class", "final_cart", "kind", "sub_kind", "split"]
    tcols = ["episode_id", "seq", "actor", "kind", "text", "tool", "stage", "result"]
    for s in SPLITS:
        for f in glob.glob(str(DATA / "messages" / "*" / f"{s}-*.parquet")):
            for r in pq.read_table(f, columns=mcols, filters=[("episode_id", "in", list(eids))]).to_pylist():
                msgs[r["episode_id"]] = r
        for f in glob.glob(str(DATA / "turns" / f"{s}-*.parquet")):
            for x in pq.read_table(f, columns=tcols, filters=[("episode_id", "in", list(eids))]).to_pylist():
                turns.setdefault(x["episode_id"], []).append(x)
    miss = sorted((eids - set(msgs)) | (eids - set(turns)))
    if miss:
        raise InputError(f"episodes not found in any split ({len(miss)}): {miss[:5]}")
    return msgs, {e: sorted(v, key=lambda z: z["seq"]) for e, v in turns.items()}


CHECKOUT_TOOLS = {"create_checkout", "update_checkout", "get_checkout", "start_checkout", "choose_fulfillment",
                  "set_shipping_address", "create_checkout_session", "update_checkout_session", "get_checkout_session",
                  "request_cart_mandate", "create_checkout_mandate"}
DAYS_RE = re.compile(r"(\d+)\s*-\s*(\d+)\s*(?:business\s+)?days?", re.I)


def _walk(o, fn):
    if isinstance(o, dict):
        fn(o)
        for v in o.values():
            _walk(v, fn)
    elif isinstance(o, list):
        for v in o:
            _walk(v, fn)


def checkout_facts(T: list, t: float) -> dict:
    """Structured checkout state before t (platform facts): fulfillment method and the selected option's max days.
    Only an option that is marked selected (selected_option / *_option_id) or a fulfillment expectation counts;
    an offered list without a selection gives no deadline fact."""
    res = [x for x in T if x["kind"] == "tool_result" and x["tool"] in CHECKOUT_TOOLS and x["seq"] < t]
    if not res:
        return {}
    o = json.loads(res[-1]["result"] or "null")
    while isinstance(o, str):
        o = json.loads(o)
    methods, sel_ids, sel_texts, opts = set(), set(), [], {}

    def look(d):
        for k in ("type", "method"):
            v = str(d.get(k) or "").lower()
            if v in ("shipping", "delivery"):
                methods.add("ship")
            elif v in ("pickup", "pick_up", "store_pickup"):
                methods.add("pickup")
        for k in ("selected_option", "selected_option_id", "selected_fulfillment_option_id", "fulfillment_option_id"):
            v = d.get(k)
            if isinstance(v, dict):
                sel_texts.append(json.dumps(v))
            elif v:
                sel_ids.add(str(v))
        if d.get("id") is not None and (d.get("title") or d.get("description")):
            opts[str(d["id"])] = str(d.get("title") or d.get("description"))
        for e in d.get("expectations") or []:
            if isinstance(e, dict):
                sel_texts.append(str(e.get("description") or ""))
    _walk(o, look)
    sel_texts += [opts[i] for i in sel_ids if i in opts]
    days = [int(m.group(2)) for s in sel_texts for m in DAYS_RE.finditer(s)]
    return {"fulfillment": next(iter(methods)) if len(methods) == 1 else None, "max_days": max(days) if days else None}


def build_case(eid: str, msg: dict, T: list, source="original") -> IntegratedCase:
    t, t_kind = decision_point(T)
    ut = [UserTurn(f"s{x['seq']}", x["seq"], x["text"]) for x in T
          if x["kind"] == "message" and x["actor"] == "shopper" and (x["text"] or "").strip() and x["seq"] < t]
    at = [(x["seq"], x["text"]) for x in T if x["kind"] == "message" and x["actor"] == "agent"
          and (x["text"] or "").strip() and x["seq"] < t]
    reg = build_registry([x for x in T if x["seq"] < t])
    try:
        fc = json.loads(msg["final_cart"] or "{}")
    except json.JSONDecodeError:
        fc = {}
    lines = fc.get("lines") or []
    if not ut:
        raise InputError(f"{eid}: no shopper turn before t={t}")
    if not lines:
        raise InputError(f"{eid}: empty payment-request cart")
    if not reg.products:
        raise InputError(f"{eid}: no catalog candidates before t")
    seller = next(iter(sorted({m for x in T if x["kind"] == "tool_result" and x["seq"] < t
                               for m in re.findall(r"ct-\d+\.example", x["result"] or "")})), f"store:{eid}")
    offers, catalog, unavailable = [], {}, []
    for p in reg.products.values():
        for vid, v in p.variants.items():
            if (seller, vid) in catalog:      # the same variant listed under two product records: first wins
                continue
            price = v["price"]
            if price is not None:
                offers.append({"cart_id": vid, "seller": seller, "label": (v["title"] or p.title) + ". " + p.description[:1500],
                               "amount": f"{price:.2f}", "currency": "USD"})
            catalog[(seller, vid)] = LineV2(seller, vid, float(price or 0.0), 1, p.brand, p.product_id, frozenset(),
                                            title=v["title"] or p.title, kind_text=p.kind_text, product_id=p.product_id,
                                            brand_known=bool(p.brand))
            if v["available"] is False:
                unavailable.append((seller, vid))
    cart = []
    for l in lines:
        vid = norm_id(l.get("variant_id"))
        key = (seller, vid)
        if key in catalog:   # payment-request price overrides the catalog price for the charged line
            c = catalog[key]
            catalog[key] = LineV2(**{**c.__dict__, "unit_price": (l.get("unit_price") or 0) / 100})
        cart.append((key, int(l.get("quantity") or 1)))
    return IntegratedCase(eid, msg["split"], source, t, t_kind, ut, at, reg, seller, offers, catalog, cart, unavailable,
                          checkout_facts={**(checkout_facts(T, t) if t_kind == "consent_request" else {}),
                                          "payment_total": (fc.get("total") / 100) if isinstance(fc.get("total"), (int, float)) else None},
                          scoring={"outcome": msg["outcome_class"], "hidden_spec": msg["hidden_spec"],
                                   "final_cart": msg["final_cart"]})   # final_cart: for the PLAN_v3 bridge row only


def build_cases(eids) -> dict:
    msgs, turns = load_rows(set(eids))
    cases = {e: build_case(e, msgs[e], turns[e]) for e in sorted(eids)}
    if len(cases) != len(set(eids)):
        raise InputError("built cases != requested episodes")
    return cases
