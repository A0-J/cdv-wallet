"""Three-stage evidence check for opening a conditional clause.

E1 source     the evidence was produced by the issuer it names (ECDSA P-256 signature; the verifier
              holds only the issuer's public key. MockHmacKey only in the ablation)
E2 authority  the issuer may assert this predicate about this subject
E3 condition  subject, predicate, freshness (TTL), session binding, single use (nonce), scope rule

E2 and Standing. Standing (Louck, Dvir, Stulman, arXiv 2610.17952) admits a claim iff
s = u or s in AUTHORITY(p). Under that rule a seller asserting its own item is out of stock is
always admitted. Here the clause's `proof` decides which roles count:
  proof = ("platform",)                       narrower than Standing: a seller's own stock claim
                                              does not open the clause (deliberate, stated as such)
  proof = ("platform", "seller_of_subject")   Standing's rule for this predicate
The "criteria" predicate (M2b) has no authority for any environment party: AUTHORITY = {}.
That is an extension of Standing (injected criteria have no subject in the option set),
not an application of it.
"""
from __future__ import annotations

from dataclasses import dataclass

from .canon import sign, verify
from .mandate import Clause, Line

AUTHORITY: dict[str, frozenset] = {
    "out_of_stock": frozenset({"platform"}),
    "price": frozenset({"platform"}),
    "criteria": frozenset(),          # extension: no environment party may set the user's criteria
}


def admissible(speaker_role: str, speaker_id: str, subject_owner: str, predicate: str,
               proof: tuple[str, ...]) -> bool:
    """Standing's rule restricted by the clause's proof list.

    speaker_role: "platform" or "seller"; speaker_id: the seller id when role is "seller".
    """
    if predicate not in AUTHORITY:
        return False
    if speaker_role == "seller":
        return speaker_id == subject_owner and "seller_of_subject" in proof     # s = u
    return speaker_role in AUTHORITY[predicate] and speaker_role in proof         # s in AUTHORITY(p)


@dataclass(frozen=True)
class Evidence:
    issuer_id: str            # key id in the issuer registry
    subject: tuple[str, str]  # (seller, cart_id)
    predicate: str
    value: bool
    issued_at: float
    session: str
    nonce: str
    signature: str = ""

    def body(self) -> dict:
        return {"issuer_id": self.issuer_id, "subject": list(self.subject), "predicate": self.predicate,
                "value": self.value, "issued_at": self.issued_at, "session": self.session, "nonce": self.nonce}


@dataclass(frozen=True)
class Issuer:
    issuer_id: str
    role: str                 # "platform" or "seller"
    seller_id: str | None     # set when role == "seller"
    verify_key: object        # ECDSA public key (or MockHmacKey in the ablation)
    signing_key: object = None  # held by the issuer only; the harness uses it to mint evidence


class IssuerRegistry:
    def __init__(self, issuers: list[Issuer]):
        self._by_id = {i.issuer_id: i for i in issuers}

    def get(self, issuer_id: str) -> Issuer | None:
        return self._by_id.get(issuer_id)

    def sign(self, e: Evidence) -> Evidence:
        k = self._by_id[e.issuer_id].signing_key
        return Evidence(**{**e.__dict__, "signature": sign(k, e.body())})

    def public_view(self) -> "IssuerRegistry":
        """What a verifier gets: public keys only."""
        return IssuerRegistry([Issuer(i.issuer_id, i.role, i.seller_id, i.verify_key, None)
                               for i in self._by_id.values()])


class NonceStore:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def seen(self, nonce: str) -> bool:
        return nonce in self._seen

    def consume(self, nonce: str) -> None:
        self._seen.add(nonce)


def check_one(e: Evidence, clause: Clause, registry: IssuerRegistry, now: float, session: str,
              nonces: NonceStore) -> str | None:
    """Return None if the evidence passes E1-E3 for this clause's predicate, else a failure code.

    Subject matching against the clause is done by the caller (scope rule)."""
    issuer = registry.get(e.issuer_id)
    if issuer is None or not verify(issuer.verify_key, e.body(), e.signature):
        return "E1_SOURCE"
    if not admissible(issuer.role, issuer.seller_id or "", e.subject[0], e.predicate, clause.proof):
        return "E2_AUTHORITY"
    if e.predicate != clause.predicate or e.value is not True:
        return "E3_PREDICATE"
    if now - e.issued_at > clause.ttl_s or e.issued_at > now:
        return "E3_STALE"
    if e.session != session:
        return "E3_SESSION"
    if nonces.seen(e.nonce):
        return "E3_REPLAY"
    return None


def clause_open(clause: Clause, evidences: list[Evidence], captured: list[Line],
                registry: IssuerRegistry, now: float, session: str, nonces: NonceStore) -> tuple[bool, str]:
    """Decide whether the clause's trigger holds. Consumes nonces only when the clause opens."""
    subject_line = next((l for l in captured if l.key == clause.subject), None)
    if clause.scope_rule == "all_captured_sellers" and subject_line is not None and subject_line.product_ref:
        targets = [l.key for l in captured if l.product_ref == subject_line.product_ref]
    else:
        targets = [clause.subject]
    used: list[str] = []
    last_fail = "EVIDENCE_MISSING"
    for t in targets:
        cands = [e for e in evidences if tuple(e.subject) == t]
        ok = None
        for e in cands:
            code = check_one(e, clause, registry, now, session, nonces)
            if code is None:
                ok = e
                break
            last_fail = code
        if ok is None:
            return False, last_fail if cands else "EVIDENCE_MISSING"
        used.append(ok.nonce)
    for n in used:
        nonces.consume(n)
    return True, "CLAUSE_OPEN"
