"""Comparison arms on one IntegratedCase. Module switches are fixed in ARMS (the only place they are set).

Common to every arm (never removed): the user's wallet key signs a mandate (ECDSA P-256), the verifier
checks the signature, the mandate version, the session, and that the submitted cart is the one the
mandate covers; payment executes only on ALLOW. B0 means "no proposed verification module", not
"no payment security".

  arm  M1 (context verification)        mandate content                          payment-time check
  B0   off                              the submitted cart, signed (floor)       common base only
  B1   on, every unresolved item asks   the submitted cart, signed               common base only
  B2   off                              unverified FnCTOD state at t -> mandate  full M2 gate (+E2)
  B3   on, selective re-confirmation    verified C/S -> mandate                  full M2 gate (+E2)
  B4   on, every unresolved item asks   verified C/S -> mandate                  full M2 gate (+E2)
  U    reference only: hidden-spec gold conditions -> mandate, full M2 gate. Never a runtime arm.
Full M2 gate = cdv/gate.py::authorize (signature, version, session, A-VIP V1-V8 STRICT, binding H,
NOT_CAPTURED, Scope v2 incl. UNKNOWN_ATTR, conditional clauses with platform evidence E1-E3) followed by
the E2 rule (a stock/lifecycle claim spoken by the chosen offer about another offer -> CLARIFY).
Final decision: cdv/verdict.py::integrated (the only combiner).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "whisperbench"))
from adapters import avip  # noqa: E402
from cdv import verdict  # noqa: E402
from cdv.canon import new_signing_key, public_of  # noqa: E402
from cdv.evidence import Evidence, Issuer, IssuerRegistry, NonceStore  # noqa: E402
from cdv.gate import Request, authorize, combined_hash, context_record  # noqa: E402
from cdv.m1 import Entry  # noqa: E402
from cdv.mandate import Mandate, VersionRegistry  # noqa: E402
from cdv.pipeline import state_to_entries  # noqa: E402
from cdv.v2.integrate import decide_selective, ledger_to_mandate  # noqa: E402
from cdv.v2.m1v2 import Ctx, run_m1v2  # noqa: E402
from cdv.v2.scope import ScopeV2  # noqa: E402
from e2_offline import e2_fires  # noqa: E402

ARMS = {
    "B0": {"m1": False, "m2": False, "selective": False},
    "B1": {"m1": True, "m2": False, "selective": False},
    "B2": {"m1": False, "m2": True, "selective": False},
    "B3": {"m1": True, "m2": True, "selective": True},
    "B4": {"m1": True, "m2": True, "selective": False},
}
NOW = 1_800_000_000.0
USER_SK = new_signing_key()
USER_PK = public_of(USER_SK)
PLAT_SK = new_signing_key()
ISSUERS = IssuerRegistry([Issuer("platform-1", "platform", None, public_of(PLAT_SK), PLAT_SK)])
PC = "set_purchase_conditions"


class Env:
    """Per-case transaction context computed once (capture, A-VIP record, claims, platform evidence)."""

    def __init__(self, case):
        self.case = case
        self.session = f"sess-{case.episode_id}"
        self.cap = avip.capture(case.offers)
        self.chosen = case.cart[0][0]
        self.avip_r = avip.record(self.cap, self.chosen).body
        self.claims = avip.claims(self.cap)
        self.e2 = e2_fires(self.claims, self.chosen)
        self.evid = [ISSUERS.sign(Evidence("platform-1", key, "out_of_stock", True, NOW - 5, self.session,
                                           f"n-{case.episode_id}-{i}")) for i, key in enumerate(case.unavailable)]

    def sign(self, m: Mandate):
        vr = VersionRegistry()
        vr.publish(m.mandate_id, m.version)
        return m.signed(USER_SK), vr

    def base_only(self, m: Mandate):
        """Common base for arms without M2: signature, version, session, submitted cart = signed cart."""
        sm, vr = self.sign(m)
        if not sm.signature_ok(USER_PK):
            return "DENY", ["MANDATE_SIG"]
        if not vr.is_current(sm.mandate_id, sm.version):
            return "DENY", ["STALE_VERSION"]
        if sm.session != self.session:
            return "DENY", ["SESSION"]
        signed = sm.primary.cart_ids or frozenset()
        if any(k[1] not in signed for k, _ in self.case.cart):
            return "DENY", ["CART_NOT_SIGNED"]
        return "ALLOW", []

    def full_gate(self, m: Mandate):
        sm, vr = self.sign(m)
        declared = None
        for _ in range(2):                       # the agent declares the clause it relies on (as in G3)
            c_r = context_record(sm, declared, [e.nonce for e in self.evid])
            req = Request(sm, USER_PK, vr, self.session, self.case.offers, self.case.catalog, self.case.cart,
                          self.avip_r, c_r, combined_hash(avip.record_hash(self.avip_r), c_r), self.evid,
                          ISSUERS, NonceStore(), NOW)
            res = authorize(req)
            if res.codes == ["CLAUSE_MISMATCH"] and res.clause_id and declared is None:
                declared = res.clause_id
                continue
            break
        d, codes = res.decision, list(res.codes)
        if d == "ALLOW" and self.e2:
            d, codes = "CLARIFY", codes + ["E2_STOCK_CLAIM_BY_CHOSEN"]
        return d, codes


def signed_cart_mandate(env: Env) -> Mandate:
    return Mandate(f"m-{env.case.episode_id}", 1, ScopeV2(cart_ids=frozenset(k[1] for k, _ in env.case.cart)),
                   session=env.session)


def raw_ctx(states_before_t: list) -> Ctx:
    """B2: the extractor's last state before t, unverified. product_type is not a mandate field without M1."""
    final = states_before_t[-1]["state"] if states_before_t else {}
    e = state_to_entries(final)
    e.pop("ptype", None)
    return Ctx(e, None, None)


def gold_ctx(gold: dict) -> Ctx:
    e = {}
    for k, (v, _) in gold.items():
        if k == "substitute":
            continue
        val = (v,) if k in ("brand_in", "brand_out") else (tuple(f"#{i}" for i in range(v)) if k == "bundle_all" else v)  # "#i": count only
        e[k] = Entry(k, k, val)
    return Ctx(e, None, None)


def run_arms(case, states: list, nli=None, gold: dict | None = None) -> dict:
    """states: FnCTOD per-turn states [{"turn_id", "state"}] for this journey (any; cut to < t here)."""
    env = Env(case)
    st = sorted([{"seq": int(s["turn_id"][1:]), "state": s["state"]} for s in states if int(s["turn_id"][1:]) < case.t],
                key=lambda s: s["seq"])
    brands = sorted({str(b) for s in st for k in ("brand_include", "brand_exclude")
                     for b in ((s["state"].get(PC) or {}).get(k) or [])})
    m1r = run_m1v2(st, case.user_turns, case.agent_turns, case.reg, case.t, nli=nli, known_brands=brands)
    mk = lambda ctx: ledger_to_mandate(ctx, case.reg, case.seller, f"m-{case.episode_id}", 1, env.session)  # noqa: E731
    out = {"m1": {"unresolved": [(u.id, u.kind, u.codes) for u in m1r.unresolved], "rejected": m1r.rejected,
                  "selection": sorted(m1r.ctx.selection) if m1r.ctx.selection else None,
                  "selection_how": m1r.selection_how, "kind": m1r.ctx.kind,
                  "C": {e.id: (list(e.value) if isinstance(e.value, tuple) else e.value) for e in m1r.ctx.entries.values()}},
           "arms": {}}
    for name, sw in ARMS.items():
        if not sw["m2"]:
            d, codes = env.base_only(signed_cart_mandate(env))
            asks = sw["m1"] and bool(m1r.unresolved)
            out["arms"][name] = {"decision": verdict.integrated(d, codes, asks), "gate": d, "codes": codes,
                                 "m1_asks": asks}
            continue
        if not sw["m1"]:
            d, codes = env.full_gate(mk(raw_ctx(st)))
            out["arms"][name] = {"decision": verdict.integrated(d, codes, False), "gate": d, "codes": codes, "m1_asks": False}
            continue
        if sw["selective"]:
            d, codes, rel, n_comb, approx = decide_selective(m1r.ctx, m1r.unresolved, lambda c: env.full_gate(mk(c)))
            asks = d == "CLARIFY" and bool(rel)
            gd, gcodes = (env.full_gate(mk(m1r.ctx)) if asks else (d, codes))
            out["arms"][name] = {"decision": verdict.integrated(gd, gcodes, asks), "gate": gd, "codes": gcodes,
                                 "m1_asks": asks, "depends_on": rel, "combos": n_comb, "approx": approx,
                                 "unverified_items": [] if asks else [u.id for u in m1r.unresolved]}
        else:
            d, codes = env.full_gate(mk(m1r.ctx))
            asks = bool(m1r.unresolved)
            out["arms"][name] = {"decision": verdict.integrated(d, codes, asks), "gate": d, "codes": codes, "m1_asks": asks}
        m = mk(m1r.ctx)
        out["arms"][name]["deferred"] = m.primary.deferred()
    if gold is not None:
        d, codes = env.full_gate(mk(gold_ctx(gold)))
        out["U_reference"] = {"decision": verdict.integrated(d, codes, False), "codes": codes}
    out["e2_fires"] = env.e2
    out["n_offers"] = len(case.offers)
    return out
