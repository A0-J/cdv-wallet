"""Scope v2 for the integrated pipeline: constraints from the verified ledger (C) and selection (S).

violations(lines) -> definite breaches (DENY material), checked against trusted catalog fields only
unknowns(lines)   -> conditions that cannot be checked because the catalog lacks the fact
                     (UNKNOWN_ATTR:<item>:<id>). Never counted as satisfied; the gate turns them into CLARIFY.
deferred()        -> conditions that the current payment request does not carry (fulfillment, deadline at
                     cart handover). Not checked here, recorded and counted as unverified.

The PLAN_v3-era Scope (cdv/mandate.py) is unchanged; WhisperBench experiments keep using it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..mandate import Line
from .candidates import toks


@dataclass(frozen=True)
class LineV2(Line):
    title: str = ""
    kind_text: str = ""          # title + product_type + categories (structured catalog fields)
    product_id: str | None = None
    brand_known: bool = False    # brand came from a structured field


def _brand_hit(line: LineV2, names) -> bool | None:
    """True if the brand field or the title names one of `names`; False if the brand field is known and neither
    does; None if undecidable. (Dev finding 2026-11-26: the brand field sometimes holds the store name, e.g. a
    'Tide' product with brand 'Builtamart', so a title match also counts.)"""
    names = {str(n).lower() for n in names}
    t = (line.title or "").lower()
    if any(re.search(r"\b" + re.escape(n) + r"\b", t) for n in names):
        return True
    if line.brand_known and line.brand:
        b = line.brand.lower()
        return any(n == b or n in b or b in n for n in names)
    return None


def _head(word: str) -> str:
    w = word.lower()
    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w


@dataclass(frozen=True)
class ScopeV2:
    max_total: float | None = None
    quantity_exact: int | None = None
    brands: frozenset | None = None            # any-of
    brands_excluded: frozenset = frozenset()
    required_all: tuple = ()                   # bundle item names (user's words); each needs a cart line
    kind: str | None = None                    # product kind the user required (hard)
    cart_ids: frozenset | None = None          # S: chosen product ids or variant ids (cart must stay inside)
    must_include: tuple = ()                   # S in a bundle purchase: each chosen product (its id set) must be in the cart
    fulfillment: str | None = None             # deferred at cart level
    deadline_days: int | None = None           # deferred at cart level

    def violations(self, lines: list[LineV2]) -> list[str]:
        out = []
        if not lines:
            return ["EMPTY_CART"]
        total = sum(l.unit_price * l.quantity for l in lines)
        if self.max_total is not None and total > self.max_total + 1e-6:
            out.append("MAX_TOTAL")
        if self.quantity_exact is not None and sum(l.quantity for l in lines) != self.quantity_exact:
            out.append("QUANTITY")
        for l in lines:
            if self.brands is not None and _brand_hit(l, self.brands) is False:
                out.append(f"BRAND:{l.cart_id}")
            if self.brands_excluded and _brand_hit(l, self.brands_excluded) is True:
                out.append(f"BRAND_EXCLUDED:{l.cart_id}")
            if self.cart_ids is not None and l.cart_id not in self.cart_ids and (l.product_id or "") not in self.cart_ids:
                out.append(f"ITEM:{l.cart_id}")
        if self.required_all and len(lines) < len(self.required_all):
            out.append("BUNDLE_MEMBER_MISSING")
        for ids in self.must_include:
            if not any(l.cart_id in ids or (l.product_id or "") in ids for l in lines):
                out.append(f"SELECTED_MISSING:{sorted(ids)[0]}")
        return out

    def unknowns(self, lines: list[LineV2]) -> list[str]:
        out = []
        for l in lines:
            if self.brands is not None and _brand_hit(l, self.brands) is None:
                out.append(f"UNKNOWN_ATTR:brand:{l.cart_id}")
            named_allowed = self.brands is not None and _brand_hit(l, self.brands) is True
            if self.brands_excluded and _brand_hit(l, self.brands_excluded) is None and not (l.brand_known and l.brand)                     and not named_allowed:
                out.append(f"UNKNOWN_ATTR:brand_excluded:{l.cart_id}")
            if self.kind:
                heads = {_head(w) for w in toks(self.kind)}
                have = {_head(w) for w in toks(l.kind_text)}
                if heads and not (heads & have):
                    out.append(f"UNKNOWN_ATTR:kind:{l.cart_id}")
        if self.required_all and len(lines) >= len(self.required_all):
            for name in self.required_all:
                if name.startswith("#"):      # count-only member (reference arm built from a member count)
                    continue
                if not any(len(toks(name) & toks(l.title)) >= max(1, len(toks(name)) // 2) for l in lines):
                    out.append(f"UNKNOWN_ATTR:bundle:{name[:30]}")
        return out

    def deferred(self) -> list[str]:
        return [k for k in ("fulfillment", "deadline_days") if getattr(self, k) is not None]

    def as_dict(self) -> dict:
        def s(x):
            return None if x is None else sorted(x)
        return {"v": 2, "max_total": self.max_total, "quantity_exact": self.quantity_exact, "brands": s(self.brands),
                "brands_excluded": sorted(self.brands_excluded), "required_all": list(self.required_all),
                "kind": self.kind, "cart_ids": s(self.cart_ids), "must_include": [sorted(x) for x in self.must_include],
                "fulfillment": self.fulfillment,
                "deadline_days": self.deadline_days}
