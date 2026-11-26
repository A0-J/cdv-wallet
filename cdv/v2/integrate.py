"""Verified context -> Mandate (ledger_to_mandate) and selective re-confirmation (decide_selective).

ledger_to_mandate(ctx, reg, seller)  Ctx (C entries, kind, S) -> unsigned Mandate with ScopeV2 primary and
                                     conditional substitution clauses F_k:
  budget_max -> max_total | quantity -> quantity_exact | brand_in -> brands | brand_out -> brands_excluded
  bundle_all -> required_all | kind -> kind | S -> cart_ids (product ids + their variant ids)
  fulfillment, deadline_days -> deferred (not carried by a cart; counted as unverified)
  substitute (accepted by V-C/V-S) and S non-empty -> one clause per S variant: if the platform shows it
  out of stock, a cart within the same constraints (named alternatives -> those brands) is allowed.
  S empty (user delegated) -> no cart_ids: any product satisfying every constraint in C is allowed.

decide_selective(base, items, gate_fn)  ask only if the decision depends on unresolved items, jointly:
  every combination of the items' variants is evaluated (cartesian product, capped); if the gate's
  decision differs across combinations -> CLARIFY naming the items whose toggling changes it.
  If all combinations agree, that decision stands and the items are recorded as unverified.
"""
from __future__ import annotations

import itertools

from ..mandate import Clause, Mandate
from .m1v2 import Ctx
from .scope import ScopeV2

MAX_COMBOS = 64


def selection_ids(ctx: Ctx, reg) -> list[frozenset]:
    """One id set per chosen product: the product id and all its variant ids."""
    out = []
    for pid in sorted(ctx.selection or ()):
        p = reg.products.get(pid) if reg else None
        out.append(frozenset({pid} | (set(p.variants) if p else set())))
    return out


def scope_from(ctx: Ctx, reg, with_selection=True) -> ScopeV2:
    e = {x.field: x for x in ctx.entries.values()}
    ids, must = None, ()
    if with_selection and ctx.selection:
        if "bundle_all" in e:   # bundle: a pick chooses one member; the other members stay free within C
            must = tuple(selection_ids(ctx, reg))
        else:                   # single item: the cart must stay inside the chosen products
            ids = set().union(*selection_ids(ctx, reg))
    return ScopeV2(
        max_total=float(e["budget_max"].value) if "budget_max" in e else None,
        quantity_exact=int(e["quantity"].value) if "quantity" in e else None,
        brands=frozenset(str(b) for b in e["brand_in"].value) if "brand_in" in e else None,
        brands_excluded=frozenset(str(b) for b in e["brand_out"].value) if "brand_out" in e else frozenset(),
        required_all=tuple(str(x) for x in e["bundle_all"].value) if "bundle_all" in e else (),
        kind=ctx.kind,
        cart_ids=frozenset(ids) if ids is not None else None,
        must_include=must,
        fulfillment=str(e["fulfillment"].value) if "fulfillment" in e else None,
        deadline_days=int(e["deadline_days"].value) if "deadline_days" in e else None)


def _ids(pids, reg) -> set:
    out = set()
    for pid in pids or ():
        p = reg.products.get(pid) if reg else None
        out |= {pid} | (set(p.variants) if p else set())
    return out


def ledger_to_mandate(ctx: Ctx, reg, seller: str, mandate_id: str, version: int, session: str,
                      chain_head: str | None = None) -> Mandate:
    prim = scope_from(ctx, reg)
    if ctx.alternatives and prim.cart_ids is not None:       # either-or: both are inside the primary scope
        prim = ScopeV2(**{**prim.__dict__, "cart_ids": frozenset(set(prim.cart_ids) | _ids(ctx.alternatives, reg))})
    fbs = []
    sub = next((x for x in ctx.entries.values() if x.field == "substitute"), None)
    if sub is not None and ctx.selection:
        then = scope_from(ctx, reg, with_selection=False)
        named = (sub.scope or {}).get("named")
        alts = ((sub.scope or {}).get("then") or {}).get("brand_in")
        targets = set(ctx.sub_targets or ())
        if named and alts and not targets and reg is not None:   # a named alternative that is a listed product
            for a in alts:
                p, _ = reg.best_match(str(a), float("inf"), min_overlap=0.6)
                if p is not None:
                    targets.add(p.product_id)
        if targets:                                           # substitution to identified products only
            then = ScopeV2(**{**then.__dict__, "cart_ids": frozenset(_ids(targets, reg))})
        elif named and alts:
            then = ScopeV2(**{**then.__dict__, "brands": frozenset(str(a) for a in alts)})
        subjects = set()
        for pid in ctx.selection:                     # the chosen products' variants (= the product itself if no variants)
            p = reg.products.get(pid) if reg else None
            subjects |= set(p.variants) if p and p.variants else {pid}
        for vid in sorted(subjects):
            fbs.append(Clause(f"fb-{vid}", (seller, vid), "out_of_stock", then=then, proof=("platform",)))
    basis = {"C": {x.id: list(x.basis) for x in ctx.entries.values()}, "S": sorted(ctx.selection or [])}
    return Mandate(mandate_id, version, prim, tuple(fbs), basis, chain_head, session)


def decide_selective(base: Ctx, items: list, gate_fn):
    """gate_fn(ctx) -> (decision, codes). Returns (decision, codes, relevant_item_ids, combos_evaluated, approx)."""
    if not items:
        d, c = gate_fn(base)
        return d, c, [], 1, False
    variant_lists = [it.variants for it in items]
    total = 1
    for v in variant_lists:
        total *= len(v)
    approx = total > MAX_COMBOS
    if not approx:
        combos = list(itertools.product(*[range(len(v)) for v in variant_lists]))
    else:   # current state, each single toggle, and all-alternatives-first
        zero = tuple(0 for _ in items)
        combos = [zero] + [tuple(j if k == i else 0 for k in range(len(items)))
                           for i, v in enumerate(variant_lists) for j in range(1, len(v))]
        combos.append(tuple(1 if len(v) > 1 else 0 for v in variant_lists))
    results = {}
    for cb in combos:
        c = base
        for it, j in zip(items, cb):
            c = it.variants[j][1](c)
        results[cb] = gate_fn(c)
    decisions = {r[0] for r in results.values()}
    if len(decisions) == 1:
        d, codes = next(iter(results.values()))
        return d, codes, [], len(combos), approx
    relevant = []
    for i, it in enumerate(items):
        for cb, r in results.items():
            for j in range(len(it.variants)):
                alt = cb[:i] + (j,) + cb[i + 1:]
                if alt in results and results[alt][0] != r[0]:
                    relevant.append(it.id)
                    break
            if it.id in relevant:
                break
    return "CLARIFY", [f"DEPENDS_ON:{x}" for x in relevant], relevant, len(combos), approx
