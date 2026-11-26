"""M1 v2 design diagnostics. No model calls, no rule changes; PLAN_v3 results are read, never written.

D1  product_type contents in FnCTOD states (E-M1 rows, test_cross_store, descriptive)
D2  reference expressions -> agent-presented candidates -> catalog SKU (validation dialogues, no model output needed)
D3  what the M2a cart check cannot see: violating carts vs hidden-spec witnesses / predicate ops (validation + E-M1 rows)
D4  conditions scored 'unjustified' that the user actually stated (E-M1 rows)
D5  temporal leakage: user turns after the final payment-consent request; offline replay with truncated states (E-M1 rows)
Output: results/m1_v2_design_20261126/diagnostics.json (+ examples)
"""
from __future__ import annotations

import glob
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cdv.m1 import Entry, Ledger, UserTurn  # noqa: E402
from cdv.pipeline import _rule_anchor, cart_check, run_verified, state_to_entries  # noqa: E402

DATA = Path(r"C:/ct/kit/dataset/data")
RES = ROOT / "results" / "e_m1_20261126"
OUT = ROOT / "results" / "m1_v2_design_20261126"
LEGIT, VIOL = {"RIGHT", "RIGHT_BY_LUCK"}, {"WRONG", "WRONG_HIDDEN"}
SETS = ["R1_test_cross_store", "R3_test_cross_store", "R2_test_cross_store"]
PC = "set_purchase_conditions"


def jl(x):
    while isinstance(x, str):
        try:
            x = json.loads(x)
        except json.JSONDecodeError:
            return None
    return x


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 2}


def overlap(a, b):
    A, B = toks(a), toks(b)
    return len(A & B) / len(A) if A else 0.0


def load_turns(eids, splits=("train", "validation", "test_cross_store", "test_cross_template")):
    out = defaultdict(list)
    cols = ["episode_id", "seq", "actor", "kind", "text", "tool", "stage", "result", "arguments"]
    for s in splits:
        for f in glob.glob(str(DATA / "turns" / f"{s}-*.parquet")):
            for x in pq.read_table(f, columns=cols, filters=[("episode_id", "in", list(eids))]).to_pylist():
                out[x["episode_id"]].append(x)
    return {e: sorted(v, key=lambda z: z["seq"]) for e, v in out.items()}


def load_msgs(eids=None, splits=("validation",)):
    cols = ["episode_id", "hidden_spec", "final_cart", "outcome_class", "kind", "split"]
    rows = []
    for s in splits:
        for f in glob.glob(str(DATA / "messages" / "*" / f"{s}-*.parquet")):
            kw = {"filters": [("episode_id", "in", list(eids))]} if eids else {}
            rows += pq.read_table(f, columns=cols, **kw).to_pylist()
    return rows


def catalog_titles(turns):
    """All product titles the agent saw from search/lookup/get_product results: [(seq, sku, title)]."""
    out = []
    for x in turns:
        if x["kind"] == "tool_result" and x["tool"] in ("search_catalog", "lookup_catalog", "get_product"):
            r = jl(x["result"]) or {}
            prods = r.get("products") or ([r["product"]] if isinstance(r.get("product"), dict) else [])
            for p in prods:
                if not isinstance(p, dict):
                    continue
                vids = [v.get("id") for v in (p.get("variants") or []) if isinstance(v, dict)]
                out.append((x["seq"], p.get("id"), p.get("title") or "", vids))
    return out


def consent_points(turns):
    """Seqs where the shopper is asked to approve a payment: wallet/system prompt or checkout-mandate request."""
    pts = [x["seq"] for x in turns if (x["actor"] == "system" and x["kind"] == "message" and x["stage"] in ("checkout", "payment"))
           or (x["kind"] == "tool_call" and x["tool"] in ("create_checkout_mandate",))]
    return pts


# ---------------------------------------------------------------- D1

GENERIC_MAX_WORDS = 3


def d1(rows_by_set, turns):
    res = {"values": Counter(), "changes": Counter(), "pending_ptype_changes": Counter(), "examples": defaultdict(list)}
    for name, rows in rows_by_set.items():
        for r in rows:
            cats = catalog_titles(turns.get(r["episode_id"], []))
            prev = None
            pend_turns = set()
            for t in (r.get("traces") or {}).get("fnctod_r") or []:
                for o in t["ops"]:
                    if o[1] == "ptype" and o[3] == "PENDING":
                        pend_turns.add(t["seq"])
            for st in r.get("fnctod_states") or []:
                v = ((st["state"].get(PC) or {}).get("product_type"))
                if not v:
                    continue
                v = str(v)
                best = max((overlap(v, c[2]) for c in cats if c[0] < int(st["turn_id"][1:]) + 1000), default=0.0)
                nw = len(v.split())
                if re.search(r"\b(or|if unavailable|similar|either|option)\b|;", v, re.I):
                    kind = "조건·후보 혼합"
                elif best >= 0.6 and nw > GENERIC_MAX_WORDS:
                    kind = "구체 상품명(카탈로그 제목과 일치)"
                elif nw <= GENERIC_MAX_WORDS:
                    kind = "일반 종류"
                else:
                    kind = "긴 설명(카탈로그 불일치)"
                res["values"][kind] += 1
                if prev is not None and v != prev[0]:
                    ch = f"{prev[1]} → {kind}"
                    res["changes"][ch] += 1
                    if int(st["turn_id"][1:]) in pend_turns:
                        res["pending_ptype_changes"][ch] += 1
                        if len(res["examples"][ch]) < 3:
                            res["examples"][ch].append({"episode": r["episode_id"], "from": prev[0][:80], "to": v[:80]})
                prev = (v, kind)
    return {k: (dict(v) if isinstance(v, (Counter, defaultdict)) else v) for k, v in res.items()}


# ---------------------------------------------------------------- D2

REF = re.compile(r"\b(option\s*\d|number\s*\d|#\s*\d|the\s+(first|second|third|fourth|last|cheaper|cheapest|other)\s+(one|option)|"
                 r"that one|this one|the one|go with (?:the )?(?:first|second|third|\d)|(?:first|second|third) one)\b", re.I)
ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}
ENUM = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s+(.*)$", re.M)


def d2(split="validation", limit=None):
    msgs = [m for m in load_msgs(splits=(split,)) if m["kind"] == "baseline"]
    if limit:
        msgs = msgs[:limit]
    turns = load_turns({m["episode_id"] for m in msgs}, splits=(split,))
    c = Counter()
    ex = []
    for m in msgs:
        T = turns.get(m["episode_id"], [])
        cats = catalog_titles(T)
        last_agent = None
        for x in T:
            if x["kind"] != "message":
                continue
            if x["actor"] == "agent":
                last_agent = x
                continue
            if x["actor"] != "shopper":
                continue
            c["shopper_turns"] += 1
            mm = REF.search(x["text"] or "")
            if not mm:
                continue
            c["ref_turns"] += 1
            items = ENUM.findall(last_agent["text"]) if last_agent else []
            if items:
                c["ref_with_enumerated_list"] += 1
            num = re.search(r"(?:option|number|#)\s*(\d)", mm.group(0), re.I)
            word = re.search(r"(first|second|third|fourth|last)", mm.group(0), re.I)
            idx = int(num.group(1)) if num else (ORD.get(word.group(1).lower()) if word and word.group(1).lower() != "last" else (len(items) if word else None))
            target = None
            if idx and items and 1 <= idx <= len(items):
                target = items[idx - 1]
                c["ref_resolved_to_list_item"] += 1
            elif not idx and len(items) <= 1 and last_agent:
                target = last_agent["text"]
                c["ref_deictic_single_candidate"] += 1
            elif not idx:
                c["ref_deictic_ambiguous"] += 1
            if target:
                seen = [t for t in cats if t[0] < x["seq"]]
                best = max(seen, key=lambda t: overlap(t[2], target), default=None)
                if best and overlap(best[2], target) >= 0.5:
                    c["ref_linked_to_catalog_sku"] += 1
                    if len(ex) < 6:
                        ex.append({"episode": m["episode_id"], "user": (x["text"] or "")[:120], "item": target[:100], "sku": best[1],
                                   "title": best[2][:80]})
    return {"split": split, "journeys": len(msgs), "counts": dict(c), "examples": ex}


# ---------------------------------------------------------------- D3

def violation_kinds(msgs):
    c, ops = Counter(), Counter()
    for m in msgs:
        if m["outcome_class"] not in VIOL:
            continue
        h = jl(m["hidden_spec"]) or {}
        cart = jl(m["final_cart"]) or {}
        skus = [str(l.get("variant_id") or l.get("product_id")) for l in cart.get("lines") or []]
        wit = {str(w) for w in h.get("witnesses") or []}
        c["violating"] += 1
        if not skus:
            c["empty_cart"] += 1
            continue
        outside = [s for s in skus if s not in wit]
        c["cart_sku_outside_witnesses" if outside else "all_cart_skus_in_witnesses"] += 1
        for p in h.get("predicates") or []:
            sb = {str(s) for s in p.get("satisfied_by") or []}
            if sb and any(s not in sb for s in skus):
                ops[f"{p.get('op')}:{p.get('source')}"] += 1
    return {"counts": dict(c), "unsatisfied_predicate_ops_by_source": dict(ops.most_common(20))}


M2A_OPS = {"max_price", "count", "all_of", "brand"}


def d3():
    val = [m for m in load_msgs(splits=("validation",)) if m["kind"] == "baseline"]
    out = {"validation": violation_kinds(val)}
    for name in SETS:
        rows = [json.loads(l) for l in (RES / f"rows_{name}.jsonl").read_text(encoding="utf-8").splitlines() if l]
        msgs = load_msgs({r["episode_id"] for r in rows}, splits=("train", "validation", "test_cross_store", "test_cross_template"))
        out[name] = violation_kinds(msgs)
    out["m2a_checks"] = sorted(M2A_OPS) + ["(brand exclusion)"]
    return out


# ---------------------------------------------------------------- D4

def gold_all(h):
    """field -> (value, source) for every source (not only stated/on_ask)."""
    g = {}
    for p in h.get("predicates") or []:
        op, v, s = p.get("op"), p.get("value"), p.get("source")
        if op == "max_price" and isinstance(v, dict):
            g["budget_max"] = (v["amount"] / 100, s)
        elif op == "count":
            g["quantity"] = (v, s)
        elif op == "all_of":
            g["bundle_all"] = (len(v) if isinstance(v, list) else v, s)
        elif op == "brand":
            g["brand_in"] = (v, s)
        elif op == "excludes":
            g["brand_out"] = (v, s)
        elif op == "prefer":
            g["substitute"] = (True, s)
    f = (h.get("buyer") or {}).get("fulfillment") or {}
    if f:
        g["fulfillment"] = ("pickup" if f.get("value") == "pickup" else "ship", f.get("source"))
        if f.get("deadline_days"):
            g["deadline_days"] = (f["deadline_days"], f.get("source"))
    return g


def d4(rows_by_set, turns, nli=None):
    sys.path.insert(0, str(ROOT / "eval" / "e_m1"))
    from run import entry_correct, gold_fields  # noqa: E402
    c = Counter()
    by_field = Counter()
    ex = []
    for name, rows in rows_by_set.items():
        msgs = {m["episode_id"]: m for m in load_msgs({r["episode_id"] for r in rows},
                                                       splits=("train", "validation", "test_cross_store", "test_cross_template"))}
        for r in rows:
            h = jl(msgs[r["episode_id"]]["hidden_spec"])
            g, ga = gold_fields(h), gold_all(h)
            ut = [UserTurn(f"s{x['seq']}", x["seq"], x["text"] or "") for x in turns.get(r["episode_id"], [])
                  if x["kind"] == "message" and x["actor"] == "shopper"]
            final = r["fnctod_states"][-1]["state"] if r.get("fnctod_states") else {}
            for e in state_to_entries(final).values():
                if entry_correct(e, g) is not False:
                    continue
                c["scored_unjustified"] += 1
                kind = "value_mismatch" if e.field in g else ("in_spec_other_source:" + str(ga[e.field][1]) if e.field in ga else "not_in_spec")
                grounded = any(_rule_anchor(e, "add", u.text) for u in ut)
                how = "rule" if grounded else ""
                if not grounded and nli is not None:
                    from cdv.pipeline import verbalize
                    hyp = verbalize(e)
                    if hyp and any(nli.entails(u.text, hyp) for u in ut):
                        grounded, how = True, "nli"
                key = f"{kind}|{'user_stated' if grounded else 'not_found'}"
                c[key] += 1
                by_field[f"{e.field}|{key}"] += 1
                if grounded and len(ex) < 10:
                    u = next((u for u in ut if _rule_anchor(e, "add", u.text)), None)
                    ex.append({"episode": r["episode_id"], "set": name, "field": e.field, "value": e.value, "kind": kind, "how": how,
                               "utterance": (u.text if u else "")[:140]})
    return {"counts": dict(c), "by_field": dict(by_field.most_common(30)), "examples": ex}


# ---------------------------------------------------------------- D5

def d5(rows_by_set, turns, nli=None):
    out = {}
    for name, rows in rows_by_set.items():
        c = Counter()
        changed = Counter()
        legit_viol = {"legit": Counter(), "viol": Counter()}
        for r in rows:
            T = turns.get(r["episode_id"], [])
            pts = consent_points(T)
            ut = [UserTurn(f"s{x['seq']}", x["seq"], x["text"] or "") for x in T if x["kind"] == "message" and x["actor"] == "shopper"]
            if not pts:
                c["no_consent_point"] += 1
                continue
            cut = max(pts)
            after = [u for u in ut if u.seq > cut]
            c["journeys"] += 1
            c["user_turns_after_last_consent_request"] += len(after)
            c["journeys_with_user_turns_after"] += bool(after)
            states = [dict(s, seq=int(s["turn_id"][1:])) for s in r.get("fnctod_states") or []]
            trunc = [s for s in states if s["seq"] < cut]
            ut_cut = [u for u in ut if u.seq < cut]
            if not trunc:
                c["no_state_before_cut"] += 1
                continue
            cart = [{"title": l.get("title") or "", "unit_price": (l.get("unit_price") or 0) / 100, "quantity": l.get("quantity") or 1}
                    for l in (jl(load_cart(r["episode_id"])) or {}).get("lines") or []]
            grp = "legit" if r["outcome"] in LEGIT else "viol"
            for arm, use in (("fnctod", None), ("fnctod_r", False), ("fnctod_rn", True)):
                if arm == "fnctod":
                    led = Ledger(1, tuple(state_to_entries(trunc[-1]["state"]).values()))
                    d, _ = cart_check(led, cart)
                    dec = d
                else:
                    res = run_verified(trunc, ut_cut, nli=nli if use else None)
                    d, _ = cart_check(res["ledger"], cart)
                    dec = "DENY" if d == "DENY" else ("CLARIFY" if res["hint"] == "CLARIFY" else d)
                old = r["arms"][arm]["decision"]
                changed[f"{arm}:{old}->{dec}"] += old != dec
                legit_viol[grp][f"{arm}:{dec}"] += 1
        out[name] = {"counts": dict(c), "decision_changes": {k: v for k, v in changed.items() if v},
                     "truncated_decisions": {k: dict(v) for k, v in legit_viol.items()}}
    return out


_CART = {}


def load_cart(eid):
    return _CART.get(eid)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows_by_set = {n: [json.loads(l) for l in (RES / f"rows_{n}.jsonl").read_text(encoding="utf-8").splitlines() if l] for n in SETS}
    eids = {r["episode_id"] for rows in rows_by_set.values() for r in rows}
    turns = load_turns(eids)
    for m in load_msgs(eids, splits=("train", "validation", "test_cross_store", "test_cross_template")):
        _CART[m["episode_id"]] = m["final_cart"]
    from cdv.nli import NLI
    nli = NLI()
    res = {"note": "descriptive diagnostics; no model calls; rules unchanged; PLAN_v3 results untouched",
           "D1_product_type": d1(rows_by_set, turns),
           "D2_reference_resolution_validation": d2("validation"),
           "D3_m2a_blind_spots": d3(),
           "D4_unjustified_but_stated": d4(rows_by_set, turns, nli),
           "D5_temporal_leakage": d5(rows_by_set, turns, nli)}
    (OUT / "diagnostics.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(res, ensure_ascii=False, default=str)[:6000])


if __name__ == "__main__":
    main()
