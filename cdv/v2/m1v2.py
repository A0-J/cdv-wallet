"""M1 v2 (option A): constraint state C, selection state S, unresolved items U.

Input: FnCTOD per-turn states and the dialogue, both cut BEFORE the decision point t (the caller cuts;
this module refuses states or turns at or after t). The FnCTOD schema is unchanged.

Differences from PLAN_v3 (cdv/pipeline.py::run_verified, kept unchanged for reproduction):
  1. product_type is split. A generic kind the user asked for in their own words becomes the hard
     constraint `kind`; a renaming of the same kind is not a change; a specific product name or a
     candidate list is NOT a constraint change (it is at most a hint; S changes only by user selection).
  2. S comes from the user's own selection acts resolved against the candidate registry
     (cdv/v2/candidates.py). Agent/seller text may identify the referent but never authorises anything.
  3. A change with no user basis is split:
       NON_USER_SOURCE  the value appears in agent/tool text before the turn -> rejected, prior kept
       NOT_FOUND        found nowhere (extractor paraphrase) -> not applied, kept as unresolved item in U
  4. Quantity basis needs quantity context (no bare digits: addresses, "option 1").
  5. A condition dropped by the extractor without a user cue is an omission by the extractor: the prior
     condition is kept (explicit revocation with a cue is applied, as in V-C).
  6. Every unresolved item carries its alternatives (variants) so that cdv/v2/selective.py can ask only
     when the payment decision depends on it, jointly over items (interactions).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from .. import m1
from ..m1 import ChangeOp, Entry, Ledger, UserTurn
from ..pipeline import _op_for, _rule_anchor, state_to_entries, verbalize
from .candidates import Registry, resolve_turn, toks

QTY_NOUN = re.compile(r"\b(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:x\s+)?(?:[a-z-]+\s+){0,3}?"
                      r"(?:units?|pieces?|pcs|packs?|pairs?|sets?|bottles?|boxes?|bags?|cans?|items?|copies|of each)\b", re.I)
_W = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
GENERIC_MAX_WORDS = 3
SPECIFIC_MIN_OVERLAP = 0.6


def qty_anchor(v: int, text: str) -> bool:
    if int(v) in m1.quantity_mentions(text):
        return True
    for m in QTY_NOUN.finditer(text):
        n = m.group(1).lower()
        if (int(n) if n.isdigit() else _W.get(n)) == int(v):
            return True
    return False


def rule_anchor_v2(entry: Entry | None, op: str, text: str) -> bool:
    if entry is not None and entry.field == "quantity" and op != "revoke":
        return qty_anchor(entry.value, text)
    return _rule_anchor(entry, op, text)


def anchor_v2(entry, op, turns, nli=None):
    for t in sorted(turns, key=lambda x: -x.seq):
        if rule_anchor_v2(entry, op, t.text):
            return (t.turn_id,), "rule"
    if nli is not None and entry is not None and op != "revoke":
        hyp = verbalize(entry)
        if hyp:
            for t in sorted(turns, key=lambda x: -x.seq):
                if nli.entails(t.text, hyp):
                    return (t.turn_id,), "nli"
    return (), "none"


def in_non_user_text(entry: Entry, texts: list[str]) -> bool:
    """Is the proposed value present in agent/tool text (the extractor may have copied it from there)?"""
    if entry is None:
        return False
    v = entry.value
    for t in texts:
        if entry.field in ("budget_max", "quantity", "deadline_days"):
            if m1._mentions_value(t, v) or f"{float(v):g}" in t.replace(",", ""):   # e.g. a cart total "$135.58"
                return True
        elif isinstance(v, tuple):
            if v and all(str(b).lower() in t.lower() for b in v):
                return True
        elif rule_anchor_v2(entry, "add", t):
            return True
    return False


@dataclass
class Ctx:
    """What a mandate is built from: verified constraint entries, the required kind, the selection."""
    entries: dict                      # id -> Entry  (budget, qty, brand_in, brand_out, bundle, deadline, ful, sub)
    kind: str | None = None
    selection: frozenset | None = None  # product ids chosen by the user (None = user did not choose / delegated)

    def copy(self, **kw):
        return replace(self, entries=dict(self.entries), **kw)


@dataclass
class Unresolved:
    id: str
    kind: str                          # C_PENDING | NOT_FOUND | SELECTION_UNRESOLVED | CONFLICT | OMISSION
    codes: list
    variants: list                     # list of (label, fn(Ctx)->Ctx); variants[0] is the current state


@dataclass
class M1Result:
    ctx: Ctx
    unresolved: list
    rejected: list                     # (entry id, code) proposals not applied: NON_USER_SOURCE, DROPPED_WITHOUT_CUE
    selection_how: str | None
    trace: list = field(default_factory=list)


def _set_entry(eid, e):
    def f(c: Ctx):
        n = c.copy()
        if e is None:
            n.entries.pop(eid, None)
        else:
            n.entries[eid] = e
        return n
    return f


def _ident(c):
    return c


def _is_generic(ptype: str, reg: Registry, seq: int) -> bool:
    words = ptype.split()
    if len(words) > GENERIC_MAX_WORDS or re.search(r"\bor\b|cheapest|similar|alternative|,", ptype, re.I):
        return False
    p, _ = reg.best_match(ptype, seq + 1, min_overlap=SPECIFIC_MIN_OVERLAP)
    return p is None


def _heads(s):
    return {w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in toks(s)}


def run_m1v2(states: list[dict], user_turns: list[UserTurn], agent_turns: list[tuple[int, str]], reg: Registry,
             t: float, nli=None, known_brands=()) -> M1Result:
    """states: [{"seq", "state"}] per user turn; agent_turns: [(seq, text)] agent messages; all must be < t."""
    assert all(s["seq"] < t for s in states), "state at or after the decision point"
    assert all(u.seq < t for u in user_turns), "user turn at or after the decision point"
    led = Ledger(0, ())
    kind, kind_basis = None, None
    unresolved: dict[str, Unresolved] = {}
    rejected, trace = [], []
    selection, sel_how = None, None
    prev_seq = -1
    for st in sorted(states, key=lambda s: s["seq"]):
        upto = [u for u in user_turns if u.seq <= st["seq"]]
        step = [u for u in user_turns if prev_seq < u.seq <= st["seq"]]
        non_user = [x for s, x in agent_turns if s < st["seq"]]
        new = state_to_entries(st["state"])
        ptype = new.pop("ptype", None)
        prev = led.by_id()
        ops, ev = [], []
        for k in sorted(set(prev) | set(new)):
            p, n = prev.get(k), new.get(k)
            if p is not None and n is not None and p.field == n.field and p.value == n.value and p.scope == n.scope:
                continue
            op = _op_for(p, n)
            cited, how = anchor_v2(n, op, upto, nli)
            if not cited:
                if op == "revoke":
                    rejected.append((k, "DROPPED_WITHOUT_CUE"))          # extractor omission: keep prior
                    ev.append((k, "DROPPED_WITHOUT_CUE"))
                    continue
                if in_non_user_text(n, non_user):
                    rejected.append((k, "NON_USER_SOURCE"))
                    ev.append((k, "NON_USER_SOURCE"))
                    continue
                unresolved[k] = Unresolved(k, "NOT_FOUND", [f"NOT_FOUND:{k}"],
                                           [("not_applied", _ident), ("applied", _set_entry(k, n))])
                ev.append((k, "NOT_FOUND"))
                continue
            ent = None if n is None else Entry(n.id, n.field, n.value, n.strength, cited, n.scope)
            ops.append((ChangeOp(op, k, ent, cited), how))
        res = m1.verify_turn(led, [o for o, _ in ops], upto)
        if nli is not None:
            for f in res.findings:
                if f.check == "V-B" and f.status == m1.UNDETERMINED:
                    e = res.ledger.by_id().get(f.detail)
                    h = verbalize(e) if e else None
                    if h and any(nli.entails(u.text, h) for u in upto):
                        f.status = m1.ACCEPT
        for (o, how), f in zip(ops, res.change_findings):
            if f.status in (m1.ACCEPT, m1.PENDING):
                unresolved.pop(o.entry_id, None)          # superseded by a later decision on the same entry
            if f.status == m1.PENDING:
                unresolved[o.entry_id] = Unresolved(o.entry_id, "C_PENDING", list(f.codes),
                                                    [("kept_prior", _ident), ("applied", _set_entry(o.entry_id, o.new))])
            ev.append((o.entry_id, o.op, how, f.status, f.codes))
        led = res.ledger
        # ---- kind (from product_type), only from the user's own words
        if ptype is not None:
            pv = str(ptype.value)
            if _is_generic(pv, reg, st["seq"]):
                said = [u for u in upto if _heads(pv) & _heads(u.text)]
                if kind is None:
                    if said:
                        kind, kind_basis = pv, said[-1].turn_id
                        ev.append(("kind", "set", pv))
                elif not (_heads(pv) & _heads(kind)):
                    now = [u for u in step if _heads(pv) & _heads(u.text)]
                    if now:
                        kind, kind_basis = pv, now[-1].turn_id
                        ev.append(("kind", "changed_by_user", pv))
                        unresolved.pop("kind", None)
                    elif any(_heads(pv) & _heads(x) for x in non_user):
                        rejected.append(("kind", "NON_USER_SOURCE"))
                    else:
                        unresolved["kind"] = Unresolved("kind", "NOT_FOUND", ["NOT_FOUND:kind"],
                                                        [("kept_prior", _ident), ("applied", lambda c, v=pv: c.copy(kind=v))])
            else:
                ev.append(("ptype", "specific_or_candidates_not_a_constraint", pv[:60]))
        # ---- selection: only the user's own selection acts in this step
        for u in step:
            last_agent = next((x for s, x in sorted(agent_turns, key=lambda z: -z[0]) if s < u.seq), None)
            r = resolve_turn(u.text, last_agent, u.seq, reg)
            if r.status == "RESOLVED":
                bundle = any(e.field == "bundle_all" for e in led.entries)
                # in a bundle purchase a pick chooses one member; it does not drop the other chosen members
                selection = (selection | frozenset(r.product_ids)) if (bundle and selection) else frozenset(r.product_ids)
                sel_how = r.how
                unresolved.pop("selection", None)
                ev.append(("selection", r.how, r.product_ids))
            elif r.status == "UNRESOLVED":
                opts = list(r.candidates)[:5]
                unresolved["selection"] = Unresolved(
                    "selection", "SELECTION_UNRESOLVED", [f"SELECTION_UNRESOLVED:{r.how}"],
                    [("unchanged", _ident)] + [(f"pick:{pid}", lambda c, pid=pid: c.copy(selection=frozenset({pid})))
                                               for pid in opts] + ([] if opts else [("any", lambda c: c.copy(selection=None))]))
                ev.append(("selection", "UNRESOLVED", r.how))
        trace.append({"seq": st["seq"], "events": ev, "C": {e.id: e.value for e in led.entries}, "kind": kind,
                      "S": sorted(selection) if selection else None})
        prev_seq = st["seq"]
    # a product the user spelled out in a request (target named before any list)
    if selection is None:
        named = {q.product_id for u in user_turns for q in reg.seen_before(t)   # every title token (>= 3) in the user's text
                 if q.title and len(toks(q.title)) >= 3 and toks(q.title) <= toks(u.text)}
        if named:
            selection, sel_how = frozenset(named), "named_in_request"
    # ---- final checks on the verified ledger: conflicts and omissions become unresolved items
    final = m1.verify_turn(led, [], user_turns)
    for f in final.findings:
        if f.check == "V-X" and f.status == m1.PENDING:
            for code in f.codes:
                if code.startswith("BRAND_IN_OUT:"):
                    i, o = code.split(":", 1)[1].split(",")
                    unresolved[f"conflict:{code}"] = Unresolved(f"conflict:{code}", "CONFLICT", [code],
                                                                [("as_is", _ident), ("keep_include", _set_entry(o, None)),
                                                                 ("keep_exclude", _set_entry(i, None))])
    om = m1.scan_omissions(led, user_turns, known_brands=known_brands, known_items={})
    turns_by_id = {u.turn_id: u for u in user_turns}
    for code in om.codes:
        alt = _omission_entry(code, turns_by_id)
        unresolved[f"omission:{code}"] = Unresolved(f"omission:{code}", "OMISSION", [code],
                                                    [("without", _ident)] + ([("with", alt)] if alt else []))
    ctx = Ctx({e.id: e for e in led.entries}, kind, selection)
    return M1Result(ctx, list(unresolved.values()), rejected, sel_how, trace)


def _omission_entry(code: str, turns_by_id):
    parts = code.split(":")
    kind, tid = parts[0], parts[1] if len(parts) > 1 else None
    text = turns_by_id[tid].text if tid in turns_by_id else ""
    if kind == "OMITTED_BUDGET":
        v = m1.budget_mentions(text)
        return _set_entry("budget", Entry("budget", "budget_max", v[-1], basis=(tid,))) if v else None
    if kind == "OMITTED_QUANTITY":
        v = m1.quantity_mentions(text)
        return _set_entry("qty", Entry("qty", "quantity", v[-1], basis=(tid,))) if v else None
    if kind.startswith("OMITTED_BRAND_"):
        pol, b = kind.split("_")[-1].lower(), parts[2] if len(parts) > 2 else None
        fld = "brand_in" if pol == "in" else "brand_out"
        if not b:
            return None

        def f(c, fld=fld, b=b):
            n = c.copy()
            old = n.entries.get(fld)
            vals = tuple(sorted(set((old.value if old else ())) | {b}))
            n.entries[fld] = Entry(fld, fld, vals, basis=(tid,))
            return n
        return f
    return None          # bundle / deadline / fulfillment / substitute: no payment-checkable value here
