"""Candidate registry and reference resolution for the selection state S (M1 v2, option A).

Sources (environment facts, never authority):
  - catalog tool results (search/lookup/get_product/...): product id, variant ids, title, price, brand,
    product_type, categories, availability
  - the agent's enumerated lists in its messages ("1. ...", "- ...")
A user turn selects a candidate only by its own words: an ordinal/number into the agent's last list,
a product name it mentions, or agreement ("sounds good") to a single proposed candidate. Agent or seller
text can tell WHICH product a user reference points to; it never changes what the user is allowed to buy.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

CATALOG_TOOLS = {"search_catalog", "lookup_catalog", "get_product", "search_products", "compare_products",
                 "send_intent_mandate"}
REF = re.compile(r"\b(option\s*\d|number\s*\d|#\s*\d|the\s+(first|second|third|fourth|last|cheaper|cheapest|other)\s+(one|option)|"
                 r"that one|this one|the one|go with (?:the )?(?:first|second|third|\d)|(?:first|second|third) one)\b", re.I)
ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}
ENUM = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s+(.*)$", re.M)
AGREE = re.compile(r"^\s*(?:yes|yeah|yep|sure|ok(?:ay)?|sounds good|that works|perfect|great|please do|go ahead|"
                   r"that'?s fine|fine)\b", re.I)
PICK_VERB = re.compile(r"\b(?:i'?ll (?:go with|take)|i will (?:go with|take)|go with|i'?d like|i want|i'?ll have|"
                       r"let'?s (?:go with|do)|proceed with|choose|pick)\b", re.I)
LINK_MIN = 0.5      # title-token overlap to link a list item / named product to a catalog product


def toks(s) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 2}


def overlap(a, b) -> float:
    """Share of a's tokens found in b."""
    A, B = toks(a), toks(b)
    return len(A & B) / len(A) if A else 0.0


def norm_id(x) -> str:
    """Variant/product ids appear as '498422012' or 'gid://shopify/ProductVariant/498422012'."""
    s = str(x or "")
    return s.rsplit("/", 1)[-1].split("?", 1)[0]


def dec(s):
    try:
        o = json.loads(s or "null")
        while isinstance(o, str):
            o = json.loads(o)
        return o
    except (json.JSONDecodeError, TypeError):
        return None


@dataclass
class Product:
    product_id: str
    title: str
    brand: str | None
    kind_text: str                     # title + product_type + categories (structured catalog fields)
    description: str                   # seller prose (label for A-VIP; never authority)
    variants: dict = field(default_factory=dict)   # variant id -> {"price": float|None, "available": bool|None, "title": str}
    first_seq: int = 0


def _walk(o, out):
    if isinstance(o, dict):
        if ("id" in o or "sku" in o) and ("title" in o or "metadata" in o) and ("price" in o or "price_range" in o or "variants" in o):
            out.append(o)
            # a product's own variants are read with the product, not as separate products
            for k, v in o.items():
                if k != "variants":
                    _walk(v, out)
            return
        for v in o.values():
            _walk(v, out)
    elif isinstance(o, list):
        for v in o:
            _walk(v, out)


def _price(p):
    """CartTrace prices: {"amount": cents} (UCP/ACP), {"value": dollars} (AP2 intent products), or price_range."""
    v = p.get("price")
    if isinstance(v, dict):
        if isinstance(v.get("amount"), (int, float)):
            return float(v["amount"]) / 100
        if isinstance(v.get("value"), (int, float)):
            return float(v["value"])
    elif isinstance(v, (int, float)):
        return float(v) / 100
    pr = p.get("price_range")
    if isinstance(pr, dict) and isinstance((pr.get("min") or {}).get("amount"), (int, float)):
        return float(pr["min"]["amount"]) / 100
    return None


class Registry:
    def __init__(self):
        self.products: dict[str, Product] = {}
        self.variant_to_product: dict[str, str] = {}

    def add_tool_result(self, seq: int, tool: str, result: str):
        if tool not in CATALOG_TOOLS:
            return
        ps = []
        _walk(dec(result), ps)
        for p in ps:
            pid = norm_id(p.get("id") or p.get("sku"))
            md = p.get("metadata") or {}
            desc = p.get("description")
            desc = (desc.get("plain") or desc.get("html") or "") if isinstance(desc, dict) else (desc or "")
            cats = " ".join(str(c.get("value")) for c in (p.get("categories") or []) if isinstance(c, dict))
            title = p.get("title") or ""
            prod = self.products.get(pid) or Product(pid, title, md.get("brand") or p.get("brand"),
                                                     " ".join([title, str(md.get("product_type") or ""), cats]), desc,
                                                     first_seq=seq)
            vs = [v for v in (p.get("variants") or []) if isinstance(v, dict)]
            if not vs:   # flat offer (e.g. intent-mandate products): the item itself is the variant
                vs = [{"id": p.get("sku") or p.get("id"), "price": p.get("price"), "title": title,
                       "availability": {"available": p.get("available")}}]
            for v in vs:
                vid = norm_id(v.get("id"))
                av = (v.get("availability") or {}).get("available") if isinstance(v.get("availability"), dict) else None
                prod.variants[vid] = {"price": _price(v) if _price(v) is not None else _price(p), "available": av,
                                      "title": v.get("title") or title}
                self.variant_to_product[vid] = pid
            self.products[pid] = prod

    def seen_before(self, seq: int) -> list[Product]:
        return [p for p in self.products.values() if p.first_seq < seq]

    def best_match(self, text: str, seq: int, min_overlap=LINK_MIN):
        """Unique best catalog product for a text (title overlap). Returns (product, score) or (None, score)."""
        scored = sorted(((overlap(p.title, text), p.product_id) for p in self.seen_before(seq)), reverse=True)
        if not scored or scored[0][0] < min_overlap:
            return None, (scored[0][0] if scored else 0.0)
        if len(scored) > 1 and scored[1][0] == scored[0][0]:
            return None, scored[0][0]          # tie: not unique
        return self.products[scored[0][1]], scored[0][0]


def build_registry(events) -> Registry:
    """events: dict rows with seq, kind, tool, result (tool_result rows before the decision point)."""
    reg = Registry()
    for x in events:
        if x.get("kind") == "tool_result":
            reg.add_tool_result(x["seq"], x.get("tool") or "", x.get("result") or "")
    return reg


@dataclass(frozen=True)
class Resolution:
    status: str            # NONE (no selection act) | RESOLVED | UNRESOLVED
    product_ids: tuple = ()
    how: str = ""
    candidates: tuple = ()  # for UNRESOLVED: the products the reference could mean


def resolve_turn(user_text: str, last_agent_text: str | None, seq: int, reg: Registry) -> Resolution:
    """Does this user turn select a product, and which one?  Only the user's words select."""
    text = user_text or ""
    items = ENUM.findall(last_agent_text or "")
    m = REF.search(text)
    if m:
        num = re.search(r"(?:option|number|#)\s*(\d)", m.group(0), re.I)
        word = re.search(r"(first|second|third|fourth|last)", m.group(0), re.I)
        idx = int(num.group(1)) if num else (
            (len(items) if word.group(1).lower() == "last" else ORD.get(word.group(1).lower())) if word else None)
        if idx and items and 1 <= idx <= len(items):
            p, _ = reg.best_match(items[idx - 1], seq)
            if p:
                return Resolution("RESOLVED", (p.product_id,), "list_index")
            return Resolution("UNRESOLVED", (), "list_item_not_in_catalog")
        # deictic ("that one"): one candidate in the agent's last message, or ambiguous
        cands = _candidates_in(last_agent_text, seq, reg)
        if len(cands) == 1:
            return Resolution("RESOLVED", (cands[0].product_id,), "deictic_single")
        return Resolution("UNRESOLVED", (), "deictic_ambiguous", tuple(c.product_id for c in cands))
    if PICK_VERB.search(text):
        p, sc = reg.best_match(text, seq, min_overlap=0.6)
        if p is None:
            # the user names an item by a short name: match the user's words against titles
            best = sorted(((len(toks(text) & toks(q.title)) / max(1, len(toks(q.title))), q.product_id)
                           for q in reg.seen_before(seq)), reverse=True)
            if best and best[0][0] >= 0.34 and (len(best) == 1 or best[1][0] < best[0][0]):
                return Resolution("RESOLVED", (best[0][1],), "named")
            return Resolution("NONE")
        return Resolution("RESOLVED", (p.product_id,), "named")
    if AGREE.search(text):
        cands = _candidates_in(last_agent_text, seq, reg)
        if len(cands) == 1:
            return Resolution("RESOLVED", (cands[0].product_id,), "agree_single_proposal")
    return Resolution("NONE")


def _candidates_in(agent_text, seq, reg: Registry) -> list[Product]:
    if not agent_text:
        return []
    items = ENUM.findall(agent_text)
    chunks = items if items else [agent_text]
    found = {}
    for ch in chunks:
        p, _ = reg.best_match(ch, seq)
        if p:
            found[p.product_id] = p
    return list(found.values())
