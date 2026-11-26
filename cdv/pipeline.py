"""Extractor state -> ledger -> M1 verification -> cart check (M2). Shared by E-M1 and the walkthrough.

Arms (same extractor output; only verification differs):
  plain       plain-LLM extraction, applied as is
  fnctod      FnCTOD extraction, applied as is
  fnctod_r    FnCTOD + M1 rules (anchoring by rules, V-C, V-P, V-X, V-S, omission scan)
  fnctod_rn   FnCTOD + M1 rules + NLI (NLI only anchors/grounds statements; it never judges legitimacy)
FnCTOD gives no citations, so M1 searches the user turns itself for each change's basis.
"""
from __future__ import annotations

import re
import time

from . import m1
from .m1 import ChangeOp, Entry, Ledger, UserTurn

PC, SP = "set_purchase_conditions", "set_substitution_policy"


def _num(x):
    try:
        return float(str(x).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def state_to_entries(state: dict) -> dict[str, Entry]:
    pc, sp = state.get(PC) or {}, state.get(SP) or {}
    e: dict[str, Entry] = {}
    b = _num(pc.get("budget_max"))
    if b is not None and b > 0:
        e["budget"] = Entry("budget", "budget_max", b)
    q = _num(pc.get("quantity"))
    if q is not None and q > 0:
        e["qty"] = Entry("qty", "quantity", int(q))
    for key, fld in (("brand_include", "brand_in"), ("brand_exclude", "brand_out")):
        v = pc.get(key)
        if isinstance(v, str):
            v = [v]
        if v:
            e[fld] = Entry(fld, fld, tuple(str(x) for x in v))
    items = pc.get("required_items")
    if isinstance(items, list) and len(items) >= 2:
        e["bundle"] = Entry("bundle", "bundle_all", tuple(str(x) for x in items))
    d = _num(pc.get("deadline_days"))
    if d is not None and d > 0:
        e["deadline"] = Entry("deadline", "deadline_days", int(d))
    f = str(pc.get("fulfillment") or "").lower()
    if f in ("pickup", "ship"):
        e["ful"] = Entry("ful", "fulfillment", f)
    if pc.get("product_type"):
        e["ptype"] = Entry("ptype", "product_type", str(pc["product_type"]), strength="soft")
    if sp.get("allowed") is True:
        named = sp.get("scope") == "named"
        alts = sp.get("named_alternatives") or []
        e["sub"] = Entry("sub", "substitute", None, scope={
            "named": named, "then": {"budget_max": b, "product_type": e["ptype"].value if "ptype" in e else None,
                                     "brand_in": list(alts) if named else None}})
    return e


def _op_for(prev: Entry | None, new: Entry | None) -> str:
    if new is None:
        return "revoke"
    if prev is None:
        return "add_substitute" if new.field == "substitute" else "add"
    if new.field in ("budget_max", "deadline_days") and prev.value is not None:
        return "relax" if float(new.value) > float(prev.value) else "tighten"
    return "override"


# ---------------------------------------------------------------- anchoring (M1 finds the basis itself)

def _rule_anchor(entry: Entry | None, op: str, text: str) -> bool:
    if op == "revoke":
        return bool(m1.WIDEN_CUES.search(text))
    f, v = entry.field, entry.value
    if f in ("budget_max", "quantity", "deadline_days"):
        if f == "budget_max":
            return any(abs(x - float(v)) < max(1.0, 0.01 * float(v)) for x in m1.budget_mentions(text))
        if f == "quantity":
            return int(v) in m1.quantity_mentions(text) or bool(re.search(rf"\b{int(v)}\b", text))
        return bool(re.search(rf"\b{int(v)}\s+(?:business\s+)?days?\b", text, re.I))
    if f in ("brand_in", "brand_out"):
        return all(str(b).lower() in text.lower() for b in v)
    if f == "fulfillment":
        return any(k == v for _, k in m1.fulfillment_mentions(text))
    if f == "bundle_all":
        return bool(m1.BUNDLE_CUE.search(text)) or sum(
            1 for n in v if " ".join(str(n).lower().split()[:2]) in text.lower()) >= 2
    if f == "substitute":
        return bool(m1.CONDITIONAL_RE.search(text))
    if f == "product_type":
        return any(w in text.lower() for w in str(v).lower().split() if len(w) > 3)
    return False


def verbalize(entry: Entry) -> str | None:
    f, v = entry.field, entry.value
    return {"budget_max": lambda: f"The customer wants to spend at most ${v:g}.",
            "quantity": lambda: f"The customer wants {v} items.",
            "deadline_days": lambda: f"The customer needs delivery within {v} days.",
            "fulfillment": lambda: ("The customer will collect the order from the store." if v == "pickup"
                                    else "The customer wants the order shipped."),
            "substitute": lambda: "The customer accepts a similar item if the requested one is out of stock.",
            "brand_in": lambda: f"The customer wants the brand {', '.join(v)}.",
            "brand_out": lambda: f"The customer does not want the brand {', '.join(v)}.",
            "bundle_all": lambda: f"The customer wants to buy {', '.join(v)} together.",
            "product_type": lambda: f"The customer is looking for {v}.",
            }.get(f, lambda: None)()


def anchor(entry, op, turns: list[UserTurn], nli=None) -> tuple[tuple, str]:
    """Latest user turn that states the change. Returns (cited_turns, how)."""
    for t in sorted(turns, key=lambda x: -x.seq):
        if _rule_anchor(entry, op, t.text):
            return (t.turn_id,), "rule"
    if nli is not None and entry is not None and op != "revoke":
        hyp = verbalize(entry)
        if hyp:
            for t in sorted(turns, key=lambda x: -x.seq):
                if nli.entails(t.text, hyp):
                    return (t.turn_id,), "nli"
    return (), "none"


# ---------------------------------------------------------------- arms

def run_verified(per_turn_states: list[dict], user_turns: list[UserTurn], nli=None, known_brands=()):
    """Replay FnCTOD's per-turn states through M1. Returns final ledger, decision hint, trace."""
    led = Ledger(0, ())
    pending, trace = [], []
    t0 = time.perf_counter()
    for st in per_turn_states:
        upto = [u for u in user_turns if u.seq <= st["seq"]]
        new = state_to_entries(st["state"])
        prev = led.by_id()
        ops = []
        for k in sorted(set(prev) | set(new)):
            p, n = prev.get(k), new.get(k)
            if p is not None and n is not None and p.field == n.field and p.value == n.value and p.scope == n.scope:
                continue
            op = _op_for(p, n)
            cited, how = anchor(n, op, upto, nli)
            ent = None if n is None else Entry(n.id, n.field, n.value, n.strength, cited, n.scope)
            ops.append((ChangeOp(op, k, ent, cited), how))
        res = m1.verify_turn(led, [o for o, _ in ops], upto)
        if nli is not None:   # NLI may settle UNDETERMINED grounding of free-text entries
            for f in res.findings:
                if f.check == "V-B" and f.status == m1.UNDETERMINED:
                    e = res.ledger.by_id().get(f.detail)
                    h = verbalize(e) if e else None
                    if h and any(nli.entails(u.text, h) for u in upto):
                        f.status = m1.ACCEPT
        # an earlier PENDING item is superseded only by a later ACCEPT or PENDING on the same entry;
        # a REJECTed (ungrounded) proposal must not silently clear it (fix 2026-11-26, walkthrough case)
        superseded = {o.entry_id for (o, _), f in zip(ops, res.change_findings) if f.status in (m1.ACCEPT, m1.PENDING)}
        pending = [p for p in pending if p.entry_id not in superseded] + res.pending
        led = res.ledger
        trace.append({"seq": st["seq"], "ops": [(o.op, o.entry_id, how, f.status, f.codes)
                                                 for (o, how), f in zip(ops, res.change_findings)],
                      "ledger": {e.id: e.value for e in led.entries},
                      "findings": [(f.check, f.status, f.codes) for f in res.findings if f.status != m1.ACCEPT]})
    final = m1.verify_turn(led, [], user_turns)
    known_items = {}
    findings = [f for f in final.findings]
    om = m1.scan_omissions(led, user_turns, known_brands=known_brands, known_items=known_items)
    flags = [f for f in findings if f.status in (m1.PENDING, m1.UNDETERMINED, m1.REJECT)] + ([om] if om.status != m1.ACCEPT else [])
    hint = "CLARIFY" if (pending or flags) else "OK"
    return {"ledger": led, "hint": hint, "pending": [(p.op, p.entry_id) for p in pending],
            "flags": sorted({c for f in flags for c in f.codes}), "trace": trace,
            "verify_ms": round(1000 * (time.perf_counter() - t0), 3)}


def cart_check(led: Ledger, cart_lines: list[dict]) -> tuple[str, list[str]]:
    """M2a deterministic transaction check against the ledger. cart_lines: {title, unit_price, quantity}."""
    if not cart_lines:
        return "DENY", ["EMPTY_CART"]
    by = {e.field: e for e in led.entries}
    codes = []
    total = sum(l["unit_price"] * l.get("quantity", 1) for l in cart_lines)
    if "budget_max" in by and total > float(by["budget_max"].value) + 1e-6:
        codes.append("OVER_BUDGET")
    if "quantity" in by and sum(l.get("quantity", 1) for l in cart_lines) != int(by["quantity"].value):
        codes.append("QUANTITY")
    if "bundle_all" in by and len(cart_lines) < len(by["bundle_all"].value):
        codes.append("BUNDLE_MEMBER_MISSING")
    if "brand_in" in by and not all(any(b.lower() in l["title"].lower() for b in by["brand_in"].value) for l in cart_lines):
        codes.append("BRAND_NOT_ALLOWED")
    if "brand_out" in by and any(b.lower() in l["title"].lower() for b in by["brand_out"].value for l in cart_lines):
        codes.append("BRAND_EXCLUDED")
    return ("ALLOW" if not codes else "DENY"), codes
