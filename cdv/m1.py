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

# ---- money expressions and budget (upper-bound) mentions: specification MONEY-1 (2026-11-26) ----
# An AMOUNT is   [currency prefix] NUMBER [magnitude] [currency suffix]   with at least one currency marker:
#   NUMBER     digits, optional thousands groups ",ddd" (or " ddd" after 1-3 digits), optional decimals ".d" / ".dd"
#   magnitude  k / K (x1,000); Korean 만 before 원 (x10,000)
#   prefix     $ € £ ₩ | US$ | USD EUR GBP KRW (any case, optional space)
#   suffix     dollar(s) bucks usd eur(o)(s) gbp pound(s) won krw 원 만원
# A BUDGET MENTION is an amount bounded from above by the user, i.e. one of:
#   (a) an upper-bound phrase ends at most 3 words before the amount in the same clause
#       (under, below, less than, no more than, not more than, no higher than, up to, at most, max/maximum (of),
#        within, cap/capped (at|of), limit (is|of), ceiling (is|of), budget (is|of), spend(ing) [no more than|up to|
#        at most|under], [can't|cannot|won't|will not|don't want to|do not want to] [go|spend|pay] [over|above|more than],
#        not [go|be] [over|above], not exceed(ing), nothing [over|above], keep [it|the total|the order] [under|below|to|within])
#   (b) a bound phrase follows within 2 words in the same clause
#       (max/maximum, or less, or under, or below, at (the) most, tops,
#        [is|as|will be|would be] [the|my|our] [total|order|spending|overall] [limit|budget|cap|ceiling|max|maximum],
#        Korean 이하 / 이내 / 미만 / 까지 / 안 넘게 / 넘지 않게)
#   (c) a budget word directly governs a bare number: "budget (is|of) 200", "spend (no more than|up to|at most) 200"
# Numbers without a currency marker and without (c) are never money (days, quantities, addresses, option numbers).
# Values keep their decimals. Clause boundary: . ; ! ? or a line break.
_NUM = r"(?P<{n}>\d{{1,3}}(?:,\d{{3}})+|\d{{1,3}}(?: \d{{3}})+(?!\d)|\d+)(?P<{d}>\.\d{{1,2}})?"
_PREFIX = r"(?:US\$|[$€£₩]|(?:USD|EUR|GBP|KRW)\b)"
_SUFFIX = r"(?:만\s?원|원|dollars?\b|bucks\b|usd\b|eur(?:o?s?)?\b|gbp\b|pounds?\b|won\b|krw\b)"
MONEY_RE = re.compile(
    r"(?P<pre>" + _PREFIX + r")\s?" + _NUM.format(n="n1", d="d1") + r"(?P<k1>\s?[kK]\b)?(?:\s?(?P<s1>" + _SUFFIX + r"))?"
    r"|" + _NUM.format(n="n2", d="d2") + r"(?P<k2>\s?[kK]\b|\s?만(?=\s?원))?\s?(?P<s2>" + _SUFFIX + r")", re.I)
_UB_BEFORE = re.compile(
    r"(?:under|below|less than|no more than|not more than|no higher than|up to|at most|max(?:imum)?(?: of)?|within|"
    r"cap(?:ped)?(?: at| of)?|limit(?: is| of)?|ceiling(?: is| of)?|budget(?: is| of)?|"
    r"spend(?:ing)?(?: no more than| up to| at most| under)?|"
    r"(?:can'?t|cannot|won'?t|will not|don'?t want to|do not want to)(?: go| spend| pay)?(?: over| above| more than)|"
    r"not(?: go| be)?(?: over| above)|not exceed(?:ing)?|nothing(?: over| above)|"
    r"keep(?: it| the total| the order)?(?: under| below| to| within))"
    r"(?:\W+\w+){0,3}?\W*$", re.I)
_UB_AFTER = re.compile(
    r"^\W*(?:\w+\W+){0,2}?(?:max(?:imum)?\b|or (?:less|under|below)\b|at (?:the )?most\b|tops\b|"
    r"(?:is|as|will be|would be)(?: the| my| our)?(?: total| order| spending| overall)? (?:limit|budget|cap|ceiling|max(?:imum)?)\b|"
    r"\s*(?:이하|이내|미만|까지|안\s?넘|넘지\s?않))", re.I)
_BARE_BUDGET = re.compile(r"(?:budget(?: is| of)?|spend(?: no more than| up to| at most)?)\s+" + _NUM.format(n="n", d="d") + r"(?!\s?(?:days?|items?|units?|pcs|pieces?)\b)", re.I)
_CLAUSE = re.compile(r"[.;!?\n](?!\d)")
QTY_RE = re.compile(r"\b(\d+)\s*(?:x\b|pcs\b|pieces?\b|units?\b|of (?:them|each|it)\b)|\b(?:one|two|three|four|five) of each\b", re.I)
DEADLINE_RE = re.compile(r"\b(?:within|in|by)\s+(\d+)\s+days?\b|\bby (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
# ---- cue specifications (2026-11-26, last rule change; written from the definitions, not from dataset sentences) ----
# CONDITIONAL-1  A user turn grants a conditional substitution iff
#   (1) it states the unavailability condition of the requested item: if / when / in case / should / in the event (that)
#       + (up to 6 words) + [is|are|be|'s|'re|goes|gets|turns out to be] + an unavailability predicate
#       (out of stock, sold out, unavailable, not available, not in stock, discontinued, gone, backordered,
#        can't / cannot be found), or "if you|they can't|cannot|couldn't get|find|source ..."
#   (2) it is not immediately followed by a request to be asked instead (tell me, let me know, ask me, check with me,
#       don't substitute|swap|replace, no substitutes), and
#   (3) within the same sentence it grants an alternative: a named alternative ("Bose is fine"), a similar / comparable / equivalent / alternative /
#       substitute / replacement / closest / next best / another / other item ... is|are|would be|will be fine|ok|
#       acceptable|good|works|will do, or go with|for X, get|buy|order|take X instead, switch to X,
#       substitute|swap|replace (it) with X, feel free to|you can|you may substitute|swap|choose.
#   A standalone grant without the condition also counts: "(or) the closest (thing|one)", "a similar one is fine",
#   "substitutes are fine", "otherwise X is fine".
_UNAVAIL = (r"(?:out of stock|sold out|unavailable|not available|not in stock|discontinued|gone|back-?ordered|"
            r"(?:can'?t|cannot) be found|isn'?t available|aren'?t available)")
_COND = (r"\b(?:if|when|in case|should|in the event(?: that)?)\s+(?:[\w'-]+\s+){0,6}?"
         r"(?:(?:is|are|be|'s|'re|goes|go|gets|get|turns out to be|happens to be)\s+)?" + _UNAVAIL +
         r"|\bif (?:you|they) (?:can'?t|cannot|couldn'?t) (?:get|find|source)\b")
_ASK_INSTEAD = (r"(?![,.;]?\s*(?:just |please |then |simply )?(?:tell me|let me know|ask me|check with me|"
                r"don'?t (?:substitute|swap|replace)|do not (?:substitute|swap|replace)|no (?:substitut|swap|replacement)))")
_ALT_NOUN = (r"(?:similar|comparable|equivalent|alternative|substitute|replacement|closest|next best|another|other)"
             r"(?:\s+(?:one|ones|item|items|product|products|model|models|option|options|brand|thing))?")
_OKAY = r"(?:is|are|would be|will be|'s)\s+(?:fine|ok|okay|acceptable|good|alright|all right)|works?|will do"
_GRANT = (r"(?:\b(?:a|an|any|the)?\s*" + _ALT_NOUN + r"\s+(?:" + _OKAY + r")"
          r"|\b(?:[\w'-]+\s+){1,4}?(?:" + _OKAY + r")"          # a named alternative: "Bose is fine", "the JBL would be ok"
          r"|\bgo (?:with|for)\b|\b(?:get|buy|order|take|use|pick)\b[^.;!?]{0,40}?\binstead\b|\bswitch to\b"
          r"|\b(?:substitute|swap|replace)\b(?:\s+(?:it|them))?\s+with\b"
          r"|\b(?:feel free to|you can|you may|it'?s (?:ok|okay|fine) to)\s+(?:substitute|swap|replace|choose|pick)\b)")
_STANDALONE = (r"\bor the closest(?: thing| one)?\b|\b(?:a |any )?similar (?:one|item|product)?\s*(?:is|would be) (?:fine|ok|okay)"
               r"|\bsubstitutes? (?:is|are) (?:fine|ok|okay|acceptable)|\botherwise[, ]+(?:\w+\s){0,4}(?:is|would be) (?:fine|ok|okay)")
CONDITIONAL_RE = re.compile(r"(?:" + _COND + r")" + _ASK_INSTEAD + r"[^.;!?]{0,100}?(?:" + _GRANT + r")|" + _STANDALONE, re.I)

# WIDEN-1  A user turn is an explicit widening cue iff the user states, as their own decision, that an earlier
#   condition no longer holds or holds more loosely. Two kinds of evidence (either suffices):
#   (D) a revision marker: actually, instead, rather, after all, on second thought, scratch that, change (it|that|my|the),
#       switch (it|to), update (it|my|the), make it, let's make it
#   (W) a widening predicate on a condition:
#       raise / increase / extend / expand / stretch / bump up / up the (budget|limit) / go up to / go higher|above|over|beyond
#       / spend|pay more / can go|spend|pay|afford (up to|more|higher) ;
#       removal: don't|do not|no longer|won't need|want, no need for, forget (about), drop, remove, skip, cancel, leave out,
#       take out, without the, just the, only the ;
#       unrestricting: any brand|color|colour|size|model|kind, (it|that|brand|color|size) doesn't|does not matter,
#       no preference, not required, optional, no (budget|limit|deadline|rush|hurry), whenever is fine ;
#       admitting more options: (X) is|are fine|ok|okay|acceptable too, also fine, works too, that's fine too,
#       either|both (is|are) fine, also accept|allow|consider, open to (other|any).
#   An ordinary pick ("I'll go with X") is not a widening cue (PICK_ONLY, V-C).
_REVISION = (r"actually|instead|rather|after all|on second thought|scratch that|change (?:it|that|my|the)|"
             r"switch (?:it|to)|update (?:it|my|the)|make it|let'?s make it")
_WIDEN_PRED = (r"raise|increase|extend|expand|stretch|bump (?:it |that |the \w+ )?up|up (?:the|my) (?:budget|limit)|"
               r"go up to|go (?:higher|above|over|beyond)|(?:spend|pay) more|can (?:go|spend|pay|afford) (?:up to|more|higher)|"
               r"(?:don'?t|do not|no longer|won'?t) (?:need|want)|no need for|forget (?:about )?|drop|remove|skip|cancel|"
               r"leave out|take out|without the|just the|only the|"
               r"any (?:brand|colou?r|size|model|kind)|(?:it|that|brand|colou?r|size) (?:doesn'?t|does not) matter|"
               r"doesn'?t matter|no preference|not required|optional|no (?:budget|limit|deadline|rush|hurry)|whenever is fine|"
               r"(?:is|are) (?:fine|ok|okay|acceptable) too|also fine|works too|that'?s fine too|(?:either|both) (?:is|are) fine|"
               r"also (?:accept|allow|consider)|open to (?:other|any)")
WIDEN_CUES = re.compile(r"\b(?:" + _REVISION + r"|" + _WIDEN_PRED + r")\b", re.I)

PICK_ONLY = re.compile(r"^\s*(?:i'?ll|i will|let'?s|i'?d like to)?\s*(?:go with|take|choose|pick|proceed with)\b", re.I)


def _num(s: str) -> float:
    s = s.replace(",", "").replace(" ", "")
    return float(s)


def _amount_value(m) -> float:
    n, d = (m.group("n1"), m.group("d1")) if m.group("n1") else (m.group("n2"), m.group("d2"))
    v = float(n.replace(",", "").replace(" ", "") + (d or ""))
    k = (m.group("k1") or m.group("k2") or "").strip().lower()
    suf = (m.group("s1") or m.group("s2") or "").replace(" ", "")
    if k == "k":
        v *= 1000
    elif k == "만" or suf.startswith("만"):
        v *= 10000
    return v


def money_amounts(text: str) -> list[tuple[int, int, float]]:
    """Every AMOUNT (spec MONEY-1) as (start, end, value)."""
    return [(m.start(), m.end(), _amount_value(m)) for m in MONEY_RE.finditer(text or "")]


def budget_mentions(text: str) -> list[float]:
    """Upper-bound amounts the text states (spec MONEY-1 (a)-(c)), in text order."""
    text = text or ""
    out = []
    taken = []
    for st, en, v in money_amounts(text):
        cut = max([m.end() for m in _CLAUSE.finditer(text, 0, st)] or [0])
        before = text[cut:st]
        nxt = _CLAUSE.search(text, en)
        after = text[en:nxt.start() if nxt else len(text)]
        if _UB_BEFORE.search(before) or _UB_AFTER.search(after):
            out.append((st, v))
            taken.append((st, en))
    for m in _BARE_BUDGET.finditer(text):
        s0 = m.start("n")
        if any(a <= s0 < b for a, b in taken):
            continue
        out.append((s0, float(m.group("n").replace(",", "").replace(" ", "") + (m.group("d") or ""))))
    return [v for _, v in sorted(out)]


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


_NUMW = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
         "ten": 10, "a pair": 2, "a couple": 2}
_N = r"(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten)"
QTY_RES = [
    re.compile(r"\b(?:i'?d like|i want|i need|get me|buy me|order|send me)\s+" + _N +
               r"(?=\s*(?:[.,!?;]|$|please\b|units?\b|pieces?\b|pcs\b|packs?\b|of (?:them|these|those|it)\b))", re.I),
    re.compile(r"\bquantity(?: of| is|:)?\s+" + _N + r"\b", re.I),
    re.compile(r"\b" + _N + r"\s+of (?:them|these|those|it)\b", re.I),
    re.compile(r"\bmake it " + _N + r"\b", re.I),
]
DEADLINE_RES = [
    re.compile(r"\b(?:within|in|by)\s+(\d{1,2})\s+(?:business\s+|working\s+)?days?\b", re.I),
    re.compile(r"\b(?:by|before) (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|next week|the weekend)\b", re.I),
    re.compile(r"\b(?:express|overnight|next[- ]day|same[- ]day|fastest)\s+(?:shipping|delivery)?\b", re.I),
    re.compile(r"\bneeds? (?:it|them) (?:fast|quickly|soon)\b", re.I),
]
PICKUP_RE = re.compile(r"\b(?:pick(?:\s|-)?(?:it\s+|them\s+)?up|collect (?:it |them )?(?:in|at|from) (?:the )?store|collect (?:it |them )?(?:from|at)|in[- ]store pick ?up|store pick ?up|click and collect)\b", re.I)
SHIP_RE = re.compile(r"\b(?:ship (?:it |them )?to|deliver(?:ed)? (?:it |them )?to|delivery to|send (?:it |them )?to|send it (?:by )?(?:express|standard)|(?:standard|regular|normal|express|economy|free) (?:delivery|shipping)(?: option)?(?: is| would be)? (?:fine|ok|okay|good)|please send it express|(?:standard|regular|express) (?:delivery|shipping) please)\b", re.I)
BRAND_NEG = r"(?:no|not|avoid|except|other than|anything but|don'?t want)\s+(?:a |an |the |any )?"
BRAND_POS = r"(?:from|by|only|just|brand)\s+"


def _qty(s: str) -> int:
    s = s.lower()
    return _NUMW[s] if s in _NUMW else int(s)


def quantity_mentions(text: str) -> list[int]:
    return [_qty(m.group(1)) for r in QTY_RES for m in r.finditer(text)]


def deadline_mentioned(text: str) -> bool:
    return any(r.search(text) for r in DEADLINE_RES)


def fulfillment_mentions(text: str) -> list[tuple[int, str]]:
    out = [(m.start(), "pickup") for m in PICKUP_RE.finditer(text)]
    out += [(m.start(), "ship") for m in SHIP_RE.finditer(text)]
    return sorted(out)


def brand_mentions(text: str, known_brands) -> list[tuple[str, str]]:
    """(brand, "in"|"out") for known brands stated with a positive or negative cue."""
    out = []
    for b in known_brands:
        if not b:
            continue
        eb = re.escape(b)
        if re.search(rf"\b{BRAND_NEG}{eb}\b", text, re.I):
            out.append((b, "out"))
        elif re.search(rf"\b{BRAND_POS}{eb}\b|\b{eb}\s+(?:only|brand only|products only)\b", text, re.I):
            out.append((b, "in"))
    return out


BUNDLE_CUE = re.compile(r"\bone of each\b|\b(?:together|in one order|to one order|go together|all three|both of them)\b", re.I)


def bundle_mentioned(text: str, known_items: dict) -> list[str]:
    """Item ids named together ('X and Y', 'both', 'together', 'each') in one user turn."""
    named = [iid for iid, name in known_items.items() if name and name.lower() in text.lower()]
    if len(named) >= 2 and re.search(r"\b(?:and|together|both|each)\b", text, re.I):
        return sorted(named)
    return []


def _has(ledger: Ledger, field: str, pred=lambda v: True) -> bool:
    return any(e.field == field and pred(e.value) for e in ledger.entries)


def scan_omissions(ledger: Ledger, user_turns: list[UserTurn], known_brands=(), known_items=None) -> Finding:
    """V-B over all user turns: typed conditions the user stated that no live entry represents.

    Fields: budget, conditional substitution, quantity, brand (known brands only), required items
    (bundle, known items only), delivery deadline, fulfillment (pickup / ship). For fields that can
    be restated, only the latest statement counts (earlier ones may have been changed).
    Rule-based: misses paraphrases its patterns do not cover; those go to the NLI stage."""
    codes = []
    known_items = known_items or {}
    ordered = sorted(user_turns, key=lambda t: t.seq)
    stated_budgets = [(t, v) for t in ordered for v in budget_mentions(t.text)]
    if stated_budgets:
        t, v = stated_budgets[-1]
        if not _has(ledger, "budget_max", lambda x: abs(float(x) - v) < 1e-6):
            codes.append(f"OMITTED_BUDGET:{t.turn_id}")
    for t in ordered:
        if CONDITIONAL_RE.search(t.text) and not _has(ledger, "substitute"):
            codes.append(f"OMITTED_SUBSTITUTE:{t.turn_id}")
            break
    qs = [(t, q) for t in ordered for q in quantity_mentions(t.text)]
    if known_items:
        qs += [(t, len(known_items)) for t in ordered if re.search(r"\bone of each\b", t.text, re.I)]
        qs.sort(key=lambda x: x[0].seq)
    if qs:
        t, q = qs[-1]
        if not _has(ledger, "quantity", lambda x: int(x) == q):
            codes.append(f"OMITTED_QUANTITY:{t.turn_id}")
    for t in ordered:
        for b, pol in brand_mentions(t.text, known_brands):
            fld = "brand_in" if pol == "in" else "brand_out"
            if not _has(ledger, fld, lambda x: b.lower() in {str(v).lower() for v in _as_set(x)}):
                codes.append(f"OMITTED_BRAND_{pol.upper()}:{t.turn_id}:{b}")
    for t in ordered:
        ids = bundle_mentioned(t.text, known_items)
        if ids and not _has(ledger, "bundle_all", lambda x: set(ids) <= {str(v) for v in _as_set(x)}):
            codes.append(f"OMITTED_BUNDLE:{t.turn_id}")
            break
        if not ids and BUNDLE_CUE.search(t.text) and not _has(ledger, "bundle_all"):
            codes.append(f"OMITTED_BUNDLE:{t.turn_id}")       # catalog names differ from spoken names
            break
    dl = [t for t in ordered if deadline_mentioned(t.text)]
    if dl and not (_has(ledger, "deadline_days") or _has(ledger, "delivery_speed")):
        codes.append(f"OMITTED_DEADLINE:{dl[-1].turn_id}")
    fm = [(t, kind) for t in ordered for _, kind in fulfillment_mentions(t.text)]
    if fm:
        t, kind = fm[-1]
        if not _has(ledger, "fulfillment", lambda x: x == kind):
            codes.append(f"OMITTED_FULFILLMENT:{t.turn_id}:{kind}")
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
