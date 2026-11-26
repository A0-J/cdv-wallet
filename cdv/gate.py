"""Authorization verification at payment time (Fig. 1 section 4.5), phase 1.

Order of checks (first failure decides):
  mandate signature            DENY  MANDATE_SIG
  V9  version current          DENY  STALE_VERSION
  session binding              DENY  SESSION
  A-VIP V1-V8 (STRICT, A-LEX)  DENY  AVIP_Vn
  V12 combined hash H          DENY  BIND_MISMATCH / CHOSEN_NOT_IN_CART
  cart lines are captured      DENY  NOT_CAPTURED
  V10 scope:
    cart within P                                ALLOW
    cart within an F_k whose trigger holds (V11) ALLOW    CLAUSE_ACTIVE
    cart within an F_k whose trigger fails       CLARIFY  EVIDENCE_MISSING / E1_SOURCE / E2_AUTHORITY / E3_*
    otherwise                                    DENY     OUT_OF_SCOPE (re-approval of a new version possible)
  C_R must name the clause actually used         DENY  CLAUSE_MISMATCH

Phase 2 (M1) adds CLARIFY for decisions that rest on a pending, unverified dialogue change.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from adapters import avip

from .canon import sha256_hex
from .evidence import Evidence, IssuerRegistry, NonceStore, clause_open
from .mandate import Line, Mandate, VersionRegistry


def combined_hash(avip_record_hash: str, context_record: dict) -> str:
    return sha256_hex({"avip_r": avip_record_hash, "cdv": context_record})


def context_record(m: Mandate, clause_id: str | None, evidence_nonces: list[str]) -> dict:
    """C_R: what the context side binds next to A-VIP's record R."""
    return {"mandate_id": m.mandate_id, "version": m.version, "mandate_sig": sha256_hex(m.signature),
            "clause_id": clause_id, "evidence_nonces": sorted(evidence_nonces),
            "user_turn_chain_head": m.user_turn_chain_head}


@dataclass
class Request:
    mandate: Mandate
    user_key: object                    # user's PUBLIC key (ECDSA); the gate never holds private keys
    versions: VersionRegistry
    session: str
    offers: list[dict]                  # what the merchant returned (A-VIP capture input)
    catalog: dict                       # (seller, cart_id) -> Line with trusted attributes
    cart: list[tuple[tuple[str, str], int]]   # [(key, quantity)]
    avip_r: dict                        # A-VIP decision record body
    context_r: dict                     # C_R as bound
    bound_hash: str                     # H carried in the checkout / payment mandate
    evidences: list[Evidence] = field(default_factory=list)
    issuers: IssuerRegistry | None = None
    nonces: NonceStore | None = None
    now: float = 0.0


@dataclass
class Result:
    decision: str                       # ALLOW | CLARIFY | DENY
    codes: list[str]
    clause_id: str | None = None


def authorize(req: Request) -> Result:
    m = req.mandate
    if not m.signature_ok(req.user_key):
        return Result("DENY", ["MANDATE_SIG"])
    if not req.versions.is_current(m.mandate_id, m.version):
        return Result("DENY", ["STALE_VERSION"])
    if m.session != req.session:
        return Result("DENY", ["SESSION"])

    cap = avip.capture(req.offers)
    ok, codes = avip.verify(req.avip_r, cap, strict=True)
    if not ok:
        return Result("DENY", [f"AVIP_{c}" for c in codes])

    if combined_hash(avip.record_hash(req.avip_r), req.context_r) != req.bound_hash:
        return Result("DENY", ["BIND_MISMATCH"])
    if req.context_r.get("mandate_id") != m.mandate_id or req.context_r.get("version") != m.version:
        return Result("DENY", ["BIND_MISMATCH"])
    cart_keys = [tuple(k) for k, _ in req.cart]
    chosen = req.avip_r.get("chosen") or {}
    if (chosen.get("seller"), chosen.get("cart_id")) not in cart_keys:
        return Result("DENY", ["CHOSEN_NOT_IN_CART"])

    captured = set(cap.keys())
    if any(k not in captured or k not in req.catalog for k in cart_keys):
        return Result("DENY", ["NOT_CAPTURED"])
    lines = [Line(**{**req.catalog[tuple(k)].__dict__, "quantity": q}) for k, q in req.cart]
    captured_lines = [req.catalog[k] for k in cap.keys() if k in req.catalog]

    declared = req.context_r.get("clause_id")
    if not m.primary.violations(lines):
        if declared is not None:
            return Result("DENY", ["CLAUSE_MISMATCH"])
        return Result("ALLOW", [])

    pending: list[str] = []
    for c in m.fallbacks:
        if c.then.violations(lines):
            continue
        opened, why = clause_open(c, req.evidences, captured_lines, req.issuers, req.now, req.session,
                                  req.nonces)
        if opened:
            if declared != c.id:
                return Result("DENY", ["CLAUSE_MISMATCH"], c.id)
            return Result("ALLOW", ["CLAUSE_ACTIVE"], c.id)
        pending.append(why)
    if pending:
        return Result("CLARIFY", sorted(set(pending)))
    return Result("DENY", ["OUT_OF_SCOPE"])
