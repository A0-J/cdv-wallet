"""M1 dialogue-context verification: deterministic part (no model calls).

Separation of extraction and verification
  * The extractor (untrusted, LLM) proposes ChangeOps. It is not part of this module.
  * The verifier receives only trusted inputs:
      - UserTurns: every user-channel utterance so far, in order (not just the extractor's quotes),
      - the previous ledger (authority state) and the proposed ledger,
      - the display log (offer keys the user was shown).
    Seller text, tool prose and other external content never enter these types. An op whose
    cited basis is not a user turn is rejected (NON_USER_SOURCE).
  * Free-text relations that rules cannot decide return UNDETERMINED; they are routed to the
    NLI / LLM stage (phase 2b) and are never silently accepted.

Five checks (inputs -> outputs -> criteria are in docs/M1_DESIGN.md section 7):
  V-P preservation, V-B grounding (incl. omission scan over all user turns),
  V-C legitimate change (asymmetric: widening needs explicit support),
  V-X conflict, V-S conditional substitution basis and scope.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

ACCEPT, PENDING, REJECT, UNDETERMINED = "ACCEPT", "PENDING", "REJECT", "UNDETERMINED"

# ---------------------------------------------------------------- trusted inputs


@dataclass(frozen=True)
class UserTurn:
    turn_id: str
    seq: int
    text: str


@dataclass(frozen=True)
class Entry:
    """One condition in the authority ledger.

    field: budget_max | budget_min | brand_in | brand_out | quantity | deadline_days | item_in (any-of) |
           bundle_all (all-of) |
           product_type | substitute | pref:<name>
    strength: hard | soft | pref
    """
    id: str
    field: str
    value: object
    strength: str = "hard"
    basis: tuple = ()          # user turn ids
    scope: dict | None = None  # for substitute: {"when": ..., "then": {...}}


@dataclass(frozen=True)
class Ledger:
    version: int
    entries: tuple

    def by_id(self) -> dict:
        return {e.id: e for e in self.entries}


@dataclass(frozen=True)
class ChangeOp:
    """Proposed by the extractor. op: add | tighten | relax | override | revoke | reprioritize | add_substitute"""
    op: str
    entry_id: str
    new: Entry | None
    cited_turns: tuple


@dataclass
class Finding:
    check: str
    status: str
    codes: list = field(default_factory=list)
    detail: str = ""


# ---------------------------------------------------------------- typed extraction (rules)

_MONEY = r"(?:[$₩€£]\s?)?(\d{1,3}(?:[,\s]\d{3})+|\d+)(?:\.\d+)?\s?(?:k|K|won|원|만\s?원|dollars?|usd|krw)?"
BUDGET_MAX_RE = re.compile(
    r"(?:under|below|less than|no more than|not more than|up to|at most|max(?:imum)?|within|budget(?: is| of)?|cap(?: of)?)\s*"
    + _MONEY, re.I)
QTY_RE = re.compile(r"\b(\d+)\s*(?:x\b|pcs\b|pieces?\b|units?\b|of (?:them|each|it)\b)|\b(?:one|two|three|four|five) of each\b", re.I)
DEADLINE_RE = re.compile(r"\b(?:within|in|by)\s+(\d+)\s+days?\b|\bby (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
CONDITIONAL_RE = re.compile(
    r"\b(?:if (?:it(?:'s| is)|that(?:'s| is)|they(?:'re| are)|[\w\s-]{1,40}? (?:is|are)) (?:out of stock|unavailable|sold out|not available)"
    r"|or the closest(?: thing)?|(?:a )?similar (?:one|item|product)?\s*(?:is|would be) (?:fine|ok|okay)"
    r"|otherwise[, ]+(?:\w+\s){0,4}(?:is|would be) (?:fine|ok|okay))", re.I)

# Explicit widening cues. Widening ops (relax / revoke / scope expansion) need one of these in a
# cited user turn; ordinary picks ("I'll go with X") are not widening cues.
WIDEN_CUES = re.compile(
    r"\b(?:actually|instead|change (?:it|that|my)|raise|increase|go up to|can (?:go|spend) (?:up to|more)|"
    r"don'?t need|no longer need|forget (?:about )?|drop (?:the )?|remove (?:the )?|skip (?:the )?|"
    r"any brand|brand doesn'?t matter|doesn'?t matter|not required|optional now|that'?s fine too|"
    r"just the|only the|without the)\b", re.I)
PICK_ONLY = re.compile(r"^\s*(?:i'?ll|i will|let'?s|i'?d like to)?\s*(?:go with|take|choose|pick|proceed with)\b", re.I)


def _num(s: str) -> float:
    s = s.replace(",", "").replace(" ", "")
    return float(s)


def budget_mentions(text: str) -> list[float]:
    out = []
    for m in BUDGET_MAX_RE.finditer(text):
        try:
            v = _num(m.group(1))
        except ValueError:
            continue
        tail = text[m.end(1):m.end(1) + 4].lower()
        if "만" in tail:
            v *= 10000
        elif tail.strip().startswith("k"):
            v *= 1000
        out.append(v)
    return out


def _mentions_value(text: str, value) -> bool:
    if isinstance(value, (int, float)):
        return any(abs(v - float(value)) < 1e-6 for v in budget_mentions(text)) or bool(
            re.search(rf"\b{int(value)}\b", text.replace(",", "")))
    if isinstance(value, (set, frozenset, tuple, list)):
        return all(_mentions_value(text, v) for v in value)
    return str(value).lower() in text.lower()


# ---------------------------------------------------------------- checks


def check_source(op: ChangeOp, turns: dict[str, UserTurn]) -> Finding | None:
    """Separation rule: a change may cite user turns only."""
    if not op.cited_turns or any(t not in turns for t in op.cited_turns):
        return Finding("V-B", REJECT, ["NON_USER_SOURCE"], f"{op.entry_id}: cited {op.cited_turns}")
    return None


def check_preservation(prev: Ledger, new: Ledger, accepted: list[ChangeOp]) -> Finding:
    """V-P: every difference between prev and new is explained by an accepted op."""
    explained = {op.entry_id for op in accepted}
    p, n = prev.by_id(), new.by_id()
    codes = []
    for eid, e in p.items():
        if eid not in n and eid not in explained:
            codes.append(f"LOST:{eid}")
        elif eid in n and n[eid] != e and eid not in explained:
            codes.append(f"CHANGED:{eid}")
    for eid in n:
        if eid not in p and eid not in explained:
            codes.append(f"UNEXPLAINED_ADD:{eid}")
    return Finding("V-P", ACCEPT if not codes else REJECT, codes)


def check_grounding(entry: Entry, turns: dict[str, UserTurn]) -> Finding:
    """V-B: the entry's basis turns are user turns and (for typed fields) state its value."""
    if not entry.basis or any(t not in turns for t in entry.basis):
        return Finding("V-B", REJECT, ["NO_USER_BASIS"], entry.id)
    text = " ".join(turns[t].text for t in entry.basis)
    if entry.field in ("budget_max", "budget_min", "quantity", "deadline_days"):
        return Finding("V-B", ACCEPT if _mentions_value(text, entry.value) else REJECT,
                       [] if _mentions_value(text, entry.value) else ["VALUE_NOT_STATED"], entry.id)
    if entry.field in ("brand_in", "brand_out", "item_in", "bundle_all"):
        ok = _mentions_value(text, entry.value)
        return Finding("V-B", ACCEPT if ok else UNDETERMINED, [] if ok else ["ENTITY_NOT_LITERAL"], entry.id)
    if entry.field == "substitute":
        ok = bool(CONDITIONAL_RE.search(text))
        return Finding("V-B", ACCEPT if ok else REJECT, [] if ok else ["NO_CONDITIONAL_CUE"], entry.id)
    return Finding("V-B", UNDETERMINED, ["FREE_TEXT"], entry.id)          # NLI / LLM stage


def scan_omissions(ledger: Ledger, user_turns: list[UserTurn]) -> Finding:
    """V-B over all user turns: typed conditions the user stated that no live entry represents.

    Uses the latest budget statement only (earlier ones may have been changed)."""
    codes = []
    ordered = sorted(user_turns, key=lambda t: t.seq)
    stated_budgets = [(t, v) for t in ordered for v in budget_mentions(t.text)]
    if stated_budgets:
        t, v = stated_budgets[-1]
        if not any(e.field == "budget_max" and abs(float(e.value) - v) < 1e-6 for e in ledger.entries):
            codes.append(f"OMITTED_BUDGET:{t.turn_id}")
    for t in ordered:
        if CONDITIONAL_RE.search(t.text) and not any(e.field == "substitute" for e in ledger.entries):
            codes.append(f"OMITTED_SUBSTITUTE:{t.turn_id}")
            break
    # An omitted user condition makes the ledger more permissive than the user: hold for CLARIFY.
    return Finding("V-B", ACCEPT if not codes else PENDING, codes, "omission scan")


WIDENING = {"relax", "revoke", "add_substitute"}


def _direction(op: ChangeOp, prev: Entry | None) -> str:
    if op.op in ("relax", "revoke", "add_substitute"):
        return "widen"
    if op.op in ("tighten", "add"):
        return "narrow"
    if op.op == "override" and prev is not None and op.new is not None:
        if prev.field == "budget_max" and float(op.new.value) > float(prev.value):
            return "widen"
        if prev.field == "budget_max" and float(op.new.value) <= float(prev.value):
            return "narrow"
        if prev.field in ("brand_in", "item_in"):          # any-of lists: a subset narrows
            old, new = set(_as_set(prev.value)), set(_as_set(op.new.value))
            return "narrow" if new <= old else "widen"
        if prev.field == "bundle_all":                       # all-of requirement: dropping a member widens
            old, new = set(_as_set(prev.value)), set(_as_set(op.new.value))
            return "narrow" if new >= old else "widen"
        return "widen"                       # unknown overrides are treated as widening
    return "narrow"


def _as_set(v):
    return v if isinstance(v, (set, frozenset, tuple, list)) else [v]


def check_change(op: ChangeOp, prev: Ledger, turns: dict[str, UserTurn]) -> Finding:
    """V-C: a change is applied only if a user turn supports it; widening needs an explicit cue.

    An ambiguous pick ("I'll go with X") never revokes or overrides a hard condition."""
    bad = check_source(op, turns)
    if bad:
        bad.check = "V-C"
        return bad
    p = prev.by_id().get(op.entry_id)
    text = " ".join(turns[t].text for t in op.cited_turns)
    direction = _direction(op, p)
    if direction == "narrow":
        if op.new is not None and op.new.field in ("budget_max", "quantity", "deadline_days") \
                and not _mentions_value(text, op.new.value):
            return Finding("V-C", PENDING, ["VALUE_NOT_STATED"], op.entry_id)
        return Finding("V-C", ACCEPT, ["NARROW"], op.entry_id)
    # widening
    if op.op == "add_substitute":
        ok = bool(CONDITIONAL_RE.search(text))
        return Finding("V-C", ACCEPT if ok else PENDING, ["WIDEN"] + ([] if ok else ["NO_CONDITIONAL_CUE"]), op.entry_id)
    if PICK_ONLY.search(text) and not WIDEN_CUES.search(text) and p is not None and p.strength == "hard":
        return Finding("V-C", PENDING, ["AMBIGUOUS_PICK_NOT_REVOCATION"], op.entry_id)
    if not WIDEN_CUES.search(text):
        return Finding("V-C", PENDING, ["WIDEN_WITHOUT_EXPLICIT_CUE"], op.entry_id)
    if op.new is not None and op.new.field in ("budget_max", "quantity", "deadline_days") \
            and not _mentions_value(text, op.new.value):
        return Finding("V-C", PENDING, ["WIDEN_VALUE_NOT_STATED"], op.entry_id)
    return Finding("V-C", ACCEPT, ["WIDEN_EXPLICIT"], op.entry_id)


def check_conflicts(ledger: Ledger, turns: dict[str, UserTurn]) -> Finding:
    """V-X: typed conditions that cannot hold together. Never resolved silently here; the
    caller resolves only through an accepted explicit user change (V-C)."""
    codes = []
    es = list(ledger.entries)
    bmax = [e for e in es if e.field == "budget_max"]
    bmin = [e for e in es if e.field == "budget_min"]
    if len({float(e.value) for e in bmax}) > 1:
        codes.append("BUDGET_MAX_MULTIPLE:" + ",".join(e.id for e in bmax))
    for lo in bmin:
        for hi in bmax:
            if float(lo.value) > float(hi.value):
                codes.append(f"BUDGET_EMPTY:{lo.id},{hi.id}")
    ins = [e for e in es if e.field == "brand_in"]
    outs = [e for e in es if e.field == "brand_out"]
    if len(ins) > 1:
        inter = set.intersection(*[{str(b).lower() for b in _as_set(e.value)} for e in ins])
        if not inter:
            codes.append("BRAND_IN_EMPTY:" + ",".join(e.id for e in ins))
    for i in ins:
        allowed = {str(b).lower() for b in _as_set(i.value)}
        for o in outs:
            banned = {str(b).lower() for b in _as_set(o.value)}
            if allowed and allowed <= banned:
                codes.append(f"BRAND_IN_OUT:{i.id},{o.id}")
    q = [e for e in es if e.field == "quantity"]
    if len({int(e.value) for e in q}) > 1:
        codes.append("QUANTITY_MULTIPLE:" + ",".join(e.id for e in q))
    return Finding("V-X", ACCEPT if not codes else PENDING, codes)


def check_substitute(entry: Entry, ledger: Ledger, turns: dict[str, UserTurn]) -> Finding:
    """V-S: a conditional substitution clause is grounded in a user conditional cue and its
    `then` scope inherits every hard primary condition the user did not explicitly lift.

    scope = {"when": {"subject": ..., "predicate": "out_of_stock"},
             "then": {"brand_in": [...]|None, "budget_max": x|None, "product_type": t|None},
             "named": bool}   # named alternative ("Bose is fine") vs "closest thing"
    """
    g = check_grounding(entry, turns)
    if g.status != ACCEPT:
        g.check = "V-S"
        return g
    then = (entry.scope or {}).get("then", {})
    codes = []
    for e in ledger.entries:
        if e.id == entry.id or e.strength != "hard":
            continue
        if e.field == "budget_max":
            if then.get("budget_max") is None or float(then["budget_max"]) > float(e.value):
                codes.append(f"THEN_DROPS_BUDGET:{e.id}")
        if e.field == "product_type" and not (entry.scope or {}).get("named"):
            if then.get("product_type") != e.value:
                codes.append(f"THEN_DROPS_PRODUCT_TYPE:{e.id}")
    if (entry.scope or {}).get("named"):
        text = " ".join(turns[t].text for t in entry.basis)
        named = then.get("brand_in") or []
        if not named or not all(str(b).lower() in text.lower() for b in named):
            codes.append("THEN_NAMES_UNSTATED_ALTERNATIVE")
    elif then.get("brand_in"):
        codes.append("CLOSEST_THING_WITH_BRAND_WIDENING")
    return Finding("V-S", ACCEPT if not codes else REJECT, codes, entry.id)


# ---------------------------------------------------------------- driver


@dataclass
class TurnResult:
    ledger: Ledger
    findings: list          # checks on the resulting ledger (V-P, V-B, V-S, omission, V-X)
    pending: list           # ops held for user confirmation
    change_findings: list = field(default_factory=list)   # V-C per proposed op (rejected ops are not applied)


def verify_turn(prev: Ledger, ops: list[ChangeOp], user_turns: list[UserTurn]) -> TurnResult:
    """Apply only verified ops (selective application) and run all checks on the result.

    A rejected op is simply not applied; it does not invalidate the ledger. It is reported in
    change_findings (an attempted change without user basis)."""
    turns = {t.turn_id: t for t in user_turns}
    findings, accepted, pending, change_findings = [], [], [], []
    for op in ops:
        f = check_change(op, prev, turns)
        change_findings.append(f)
        if f.status == ACCEPT:
            accepted.append(op)
        elif f.status == PENDING:
            pending.append(op)
    entries = {e.id: e for e in prev.entries}
    for op in accepted:
        if op.op == "revoke":
            entries.pop(op.entry_id, None)
        elif op.new is not None:
            entries[op.entry_id] = op.new
    new = Ledger(prev.version + (1 if accepted else 0), tuple(entries.values()))
    findings.append(check_preservation(prev, new, accepted))
    for e in new.entries:
        if any(op.entry_id == e.id for op in accepted):
            findings.append(check_grounding(e, turns))
            if e.field == "substitute":
                findings.append(check_substitute(e, new, turns))
    findings.append(scan_omissions(new, user_turns))
    findings.append(check_conflicts(new, turns))
    return TurnResult(new, findings, pending, change_findings)


def gate_hint(result: TurnResult) -> str:
    """What the payment gate should do with this ledger: ALLOW-able, CLARIFY, or REJECT."""
    if any(f.status == REJECT for f in result.findings):
        return "REJECT"
    if result.pending or any(f.status in (PENDING, UNDETERMINED) for f in result.findings):
        return "CLARIFY"
    return "OK"
