"""Signed mandate G: primary scope P, conditional fallback clauses F_k, version.

Phase 1 (authorization first): the mandate is built from the scenario's ground truth.
Phase 2 adds M1, which derives P and F_k from the dialogue and checks each clause's basis.

Scope constraints are evaluated against trusted catalog attributes of the cart lines
(never against seller prose).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .canon import sign, verify


@dataclass(frozen=True)
class Line:
    """One cart line, keyed like A-VIP offers by (seller, cart_id)."""
    seller: str
    cart_id: str
    unit_price: float
    quantity: int = 1
    brand: str | None = None
    product_ref: str | None = None          # same product across sellers (e.g. GTIN); None if unknown
    features: frozenset = frozenset()

    @property
    def key(self) -> tuple[str, str]:
        return (self.seller, self.cart_id)


@dataclass(frozen=True)
class Scope:
    """A conjunction of constraints. None means unconstrained."""
    brands: frozenset | None = None
    max_total: float | None = None           # cart total upper bound
    required_features: frozenset = frozenset()
    max_quantity: int | None = None
    sellers: frozenset | None = None
    cart_ids: frozenset | None = None        # explicit item list (e.g. a named product)

    def violations(self, lines: list[Line]) -> list[str]:
        out: list[str] = []
        if not lines:
            return ["EMPTY_CART"]
        total = sum(l.unit_price * l.quantity for l in lines)
        if self.max_total is not None and total > self.max_total + 1e-9:
            out.append("MAX_TOTAL")
        for l in lines:
            if self.brands is not None and (l.brand or "").lower() not in {b.lower() for b in self.brands}:
                out.append(f"BRAND:{l.cart_id}")
            if not self.required_features <= l.features:
                out.append(f"FEATURES:{l.cart_id}")
            if self.sellers is not None and l.seller not in self.sellers:
                out.append(f"SELLER:{l.cart_id}")
            if self.cart_ids is not None and l.cart_id not in self.cart_ids:
                out.append(f"ITEM:{l.cart_id}")
        if self.max_quantity is not None and sum(l.quantity for l in lines) > self.max_quantity:
            out.append("QUANTITY")
        return out

    def as_dict(self) -> dict:
        def s(x):
            return None if x is None else sorted(x)
        return {"brands": s(self.brands), "max_total": self.max_total,
                "required_features": sorted(self.required_features), "max_quantity": self.max_quantity,
                "sellers": s(self.sellers), "cart_ids": s(self.cart_ids)}


@dataclass(frozen=True)
class Clause:
    """Pre-authorised conditional substitution: if `predicate` holds for `subject`, `then` opens.

    scope_rule: "subject_seller"       the subject offer itself must be shown out of stock
                "all_captured_sellers" every captured offer with the subject's product_ref must be
    proof:      issuer roles whose evidence counts, e.g. ("platform",) or ("platform", "seller_of_subject").
                ("platform",) is deliberately narrower than Standing's s = u rule (see evidence.py).
    """
    id: str
    subject: tuple[str, str]
    predicate: str
    then: Scope
    proof: tuple[str, ...] = ("platform",)
    scope_rule: str = "subject_seller"
    ttl_s: int = 600

    def as_dict(self) -> dict:
        return {"id": self.id, "subject": list(self.subject), "predicate": self.predicate,
                "then": self.then.as_dict(), "proof": list(self.proof),
                "scope_rule": self.scope_rule, "ttl_s": self.ttl_s}


@dataclass(frozen=True)
class Mandate:
    mandate_id: str
    version: int
    primary: Scope
    fallbacks: tuple[Clause, ...] = ()
    basis: dict = field(default_factory=dict)          # clause id -> user turn refs (checked by M1 later)
    user_turn_chain_head: str | None = None              # hash-chain head of user-channel turns only
    session: str = ""
    signature: str = ""

    def body(self) -> dict:
        return {"mandate_id": self.mandate_id, "version": self.version, "primary": self.primary.as_dict(),
                "fallbacks": [c.as_dict() for c in self.fallbacks], "basis": self.basis,
                "user_turn_chain_head": self.user_turn_chain_head, "session": self.session}

    def signed(self, user_signing_key) -> "Mandate":
        """Signed by the user's wallet key (ECDSA P-256 private key; MockHmacKey only in the ablation)."""
        return Mandate(self.mandate_id, self.version, self.primary, self.fallbacks, self.basis,
                       self.user_turn_chain_head, self.session, sign(user_signing_key, self.body()))

    def signature_ok(self, user_verify_key) -> bool:
        """Needs only the user's public key (ECDSA)."""
        return verify(user_verify_key, self.body(), self.signature)


class VersionRegistry:
    """Latest signed version per mandate id, and revoked versions (wallet-side state)."""

    def __init__(self) -> None:
        self._latest: dict[str, int] = {}
        self._revoked: set[tuple[str, int]] = set()

    def publish(self, mandate_id: str, version: int) -> None:
        prev = self._latest.get(mandate_id)
        if prev is not None and version <= prev:
            raise ValueError("version must increase")
        if prev is not None:
            self._revoked.add((mandate_id, prev))
        self._latest[mandate_id] = version

    def is_current(self, mandate_id: str, version: int) -> bool:
        return self._latest.get(mandate_id) == version and (mandate_id, version) not in self._revoked
