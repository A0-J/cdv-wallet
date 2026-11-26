"""M1-G in the natural extraction path (main M1, researcher decision 2026-11-26).

Same as M1 v2 (cdv/v2/m1v2.py) except the basis judgement of constraint changes:
  for every user-turn step, every field whose FnCTOD value changed (add / change / removal) is judged by M1-G
  (cdv/v2/m1g.py: that user turn + the change in plain words) ->
    decision       ACCEPT  -> applied
    question / not_mentioned -> REJECT -> the earlier value is kept
    ambiguous / unparsed     -> CLARIFY -> unresolved item (variants: kept / applied) for selective re-confirmation
  No widening-cue lexicon, no NLI. The source rule is structural: a step is a user turn by construction (FnCTOD
  states are produced per user turn); text that only the agent/seller said is judged 'not_mentioned' by M1-G.
Kept from M1 v2 (deterministic, model-free): product kind, selection S and its unresolved references, the omission
scan, brand in/out conflicts. M1 v2's own C items (C_PENDING / NOT_FOUND) are discarded: C is decided here.
"""
from __future__ import annotations

from ..m1 import Entry, UserTurn
from ..pipeline import state_to_entries
from . import m1g
from .m1v2 import Ctx, M1Result, Unresolved, _ident, _set_entry, run_m1v2


def describe_entry(old: Entry | None, new: Entry | None) -> str:
    e = new or old
    f = e.field
    if new is None:
        return {"budget_max": "Remove the spending limit.", "quantity": "Remove the quantity requirement.",
                "brand_in": "Remove the brand requirement.", "brand_out": "Remove the excluded brands.",
                "bundle_all": "Remove the requirement to buy the items together.", "deadline_days": "Remove the time limit.",
                "fulfillment": "Remove the delivery or pickup requirement.",
                "substitute": "Remove the substitution permission."}.get(f, f"Remove the {f} condition.")
    v = new.value
    if f == "budget_max":
        return f"Set the total spending limit to {float(v):.2f}."
    if f == "quantity":
        return f"Set the quantity to {int(v)}."
    if f == "brand_in":
        return f"Allow only the brand(s) {', '.join(map(str, v))}."
    if f == "brand_out":
        return f"Exclude the brand(s) {', '.join(map(str, v))}."
    if f == "bundle_all":
        return "Buy these items together: " + "; ".join(map(str, v)) + "."
    if f == "deadline_days":
        return f"Require the order within {int(v)} days."
    if f == "fulfillment":
        return "Change fulfillment to " + ("store pickup." if v == "pickup" else "home delivery.")
    if f == "substitute":
        alts = ((new.scope or {}).get("then") or {}).get("brand_in")
        return "Allow a substitute if the item is out of stock" + (f" ({', '.join(map(str, alts))})." if alts else ".")
    return f"Set {f} to {v}."


def run_m1g_path(states, user_turns: list[UserTurn], agent_turns, reg, t: float, llm, known_brands=()) -> M1Result:
    assert all(s["seq"] < t for s in states) and all(u.seq < t for u in user_turns), "input at or after the decision point"
    base = run_m1v2(states, user_turns, agent_turns, reg, t, nli=None, known_brands=known_brands)   # kind, S, omissions
    keep = [u for u in base.unresolved if u.kind in ("SELECTION_UNRESOLVED", "OMISSION", "CONFLICT")]
    entries, unresolved, rejected, trace = {}, {}, [], []
    prev_raw, prev_seq = {}, -1
    for st in sorted(states, key=lambda s: s["seq"]):
        new_raw = state_to_entries(st["state"])
        new_raw.pop("ptype", None)
        step = [u for u in user_turns if prev_seq < u.seq <= st["seq"]]
        turn = step[-1] if step else None
        ev = []
        for k in sorted(set(prev_raw) | set(new_raw)):
            p, n = prev_raw.get(k), new_raw.get(k)
            if p is not None and n is not None and p.field == n.field and p.value == n.value and p.scope == n.scope:
                continue
            if turn is None:
                rejected.append((k, "NO_USER_TURN"))
                continue
            dec, lab, _ = m1g.decide_text(llm, turn.text, describe_entry(p, n))
            if dec == "ACCEPT":
                if n is None:
                    entries.pop(k, None)
                else:
                    entries[k] = Entry(n.id, n.field, n.value, n.strength, (turn.turn_id,), n.scope)
                unresolved.pop(k, None)
            elif dec == "CLARIFY":
                unresolved[k] = Unresolved(k, "M1G_AMBIGUOUS", [f"M1G:{lab}"],
                                           [("kept_prior", _ident), ("applied", _set_entry(k, n))])
            else:
                rejected.append((k, f"M1G_{lab}"))
            ev.append((k, dec, lab))
        trace.append({"seq": st["seq"], "events": ev, "C": {e.id: e.value for e in entries.values()}})
        prev_raw, prev_seq = new_raw, st["seq"]
    ctx = Ctx(entries, base.ctx.kind, base.ctx.selection)
    return M1Result(ctx, list(unresolved.values()) + keep, rejected, base.selection_how, trace)
