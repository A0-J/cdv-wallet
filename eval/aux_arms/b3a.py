"""B3-A (asymmetric rejection) — AUXILIARY configuration declared after the policy freeze and before v4b
(researcher decision 2026-11-27, adjustment history 22). Not in the Holm family; the frozen B3 stays the main result.

Definition (fixed in results/frozen_610a97c/B3A_DEFINITION.md):
  Identical to B3 (frozen cdv/v2/m1g_path.py::run_m1g_path + selective re-confirmation + unverified-at-consent
  policy) except one rule: a change that M1-G labels "question" or "not_mentioned" (decision REJECT) is NOT rejected
  when the change NARROWS the payment authority; it becomes an unresolved item (variants: kept prior / applied),
  exactly like an "ambiguous" label. Changes at a step without a user turn are rejected as in B3.
  narrows(old, new), deterministic, per field:
    budget_max     new or lower limit                      (old None, or new < old)
    deadline_days  new or shorter time limit                (old None, or new < old)
    brand_out      exclusions added                         (old None, or new set strictly contains old set)
    brand_in       allowed brands introduced or reduced     (old None, or new set strictly inside old set)
    fulfillment    a fulfillment requirement introduced     (old None)
    substitute     substitution permission withdrawn        (new None while old exists)
    any other field / any other change (removals, quantity, bundle, swaps)  -> not narrowing
The M1-G requests are the same as B3's (they depend on the extracted states only), so with the run's ledger replayed
no extra call is made. No system code is changed (the frozen function is mirrored here with that single difference).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
from cdv.m1 import Entry  # noqa: E402
from cdv.pipeline import state_to_entries  # noqa: E402
from cdv.v2 import m1g  # noqa: E402
from cdv.v2.m1g_path import describe_entry  # noqa: E402
from cdv.v2.m1v2 import Ctx, M1Result, Unresolved, _ident, _set_entry, run_m1v2  # noqa: E402


def narrows(old, new) -> bool:
    f = (new or old).field
    ov = old.value if old is not None else None
    nv = new.value if new is not None else None
    if f in ("budget_max", "deadline_days"):
        return new is not None and (old is None or float(nv) < float(ov))
    if f == "brand_out":
        return new is not None and (old is None or set(map(str, nv)) > set(map(str, ov)))
    if f == "brand_in":
        return new is not None and (old is None or set(map(str, nv)) < set(map(str, ov)))
    if f == "fulfillment":
        return new is not None and old is None
    if f == "substitute":
        return new is None and old is not None
    return False


def run_m1g_path_asym(states, user_turns, agent_turns, reg, t, llm, known_brands=()) -> M1Result:
    """Mirror of the frozen run_m1g_path with the single B3-A rule (see module docstring)."""
    assert all(s["seq"] < t for s in states) and all(u.seq < t for u in user_turns), "input at or after the decision point"
    base = run_m1v2(states, user_turns, agent_turns, reg, t, nli=None, known_brands=known_brands)
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
            elif dec == "CLARIFY" or (dec == "REJECT" and lab in ("question", "not_mentioned") and narrows(p, n)):
                kind = "M1G_AMBIGUOUS" if dec == "CLARIFY" else "M1G_REJECT_NARROWING"
                unresolved[k] = Unresolved(k, kind, [f"M1G:{lab}"], [("kept_prior", _ident), ("applied", _set_entry(k, n))])
            else:
                rejected.append((k, f"M1G_{lab}"))
            ev.append((k, dec, lab))
        trace.append({"seq": st["seq"], "events": ev, "C": {e.id: e.value for e in entries.values()}})
        prev_raw, prev_seq = new_raw, st["seq"]
    ctx = Ctx(entries, base.ctx.kind, base.ctx.selection)
    return M1Result(ctx, list(unresolved.values()) + keep, rejected, base.selection_how, trace)


def b3_like(case, states, llm, asym: bool) -> dict:
    """B3 (asym=False, replay of the frozen path) or B3-A (asym=True) decision for one case, frozen arms helpers."""
    import arms as A
    env = A.Env(case)
    st = sorted([{"seq": int(s["turn_id"][1:]), "state": s["state"]} for s in states if int(s["turn_id"][1:]) < case.t],
                key=lambda s: s["seq"])
    brands = sorted({str(b) for s in st for k in ("brand_include", "brand_exclude") for b in ((s["state"].get(A.PC) or {}).get(k) or [])})
    if asym:
        m1r = run_m1g_path_asym(st, case.user_turns, case.agent_turns, case.reg, case.t, llm, known_brands=brands)
    else:
        m1r = A.run_m1g_path(st, case.user_turns, case.agent_turns, case.reg, case.t, llm, known_brands=brands)
    mk = lambda ctx: A.ledger_to_mandate(ctx, case.reg, case.seller, f"m-{case.episode_id}", 1, env.session)  # noqa: E731
    a = A._m1_arm(env, mk, m1r, True, case)
    if A.UNVERIFIED_POLICY == "consent_clarify" and a["decision"] == "ALLOW" and a.get("deferred"):   # as run_arms
        if case.t_kind == "consent_request":
            a["decision"] = "CLARIFY"
            a["codes"] = list(a["codes"]) + ["UNVERIFIED_AT_CONSENT:" + ",".join(a["deferred"])]
        else:
            a["proceed_unverified"] = True
    a["unresolved_kinds"] = [u.kind for u in m1r.unresolved]
    return a
