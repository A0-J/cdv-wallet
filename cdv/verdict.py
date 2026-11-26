"""Single place where an arm's final decision is formed (2026-11-26).

Every evaluation script calls these functions; none re-implements the precedence. Two diagnostics went
wrong because a second copy of this rule ranked DENY above CLARIFY (D5) — see
results/e_m1_20261126/RUN_LOG.md, section on the decision-point correction.

plan_v3(hint, m2a)            PLAN_v3 rule (eval/e_m1/run.py): an M1 CLARIFY hint wins over the M2a
                              cart check; otherwise the cart check decides. Arms without M1 pass hint=None.
integrated(base, gate, m1)    integrated pipeline (docs/INTEGRATED_EVAL_DESIGN.md):
                              1. base-integrity failure (signature, version, session, A-VIP binding,
                                 capture) -> DENY in every arm; M1 cannot override it
                              2. M1 asks (CLARIFY) -> CLARIFY
                              3. otherwise the authorization gate decides (ALLOW / CLARIFY / DENY)
"""
from __future__ import annotations

ALLOW, CLARIFY, DENY = "ALLOW", "CLARIFY", "DENY"
DECISIONS = (ALLOW, CLARIFY, DENY)

# gate codes that mean the transaction itself is not intact (common to every arm, never overridden)
BASE_INTEGRITY = ("MANDATE_SIG", "STALE_VERSION", "SESSION", "AVIP_", "BIND_MISMATCH", "CHOSEN_NOT_IN_CART",
                  "NOT_CAPTURED", "CART_NOT_SIGNED")


def plan_v3(hint: str | None, m2a: str) -> str:
    assert m2a in DECISIONS, m2a
    assert hint in (None, "OK", "CLARIFY"), hint
    return CLARIFY if hint == "CLARIFY" else m2a


def is_base_failure(codes) -> bool:
    return any(str(c).startswith(b) for c in codes for b in BASE_INTEGRITY)


def integrated(gate_decision: str, gate_codes, m1_asks: bool) -> str:
    assert gate_decision in DECISIONS, gate_decision
    if gate_decision == DENY and is_base_failure(gate_codes):
        return DENY
    if m1_asks:
        return CLARIFY
    return gate_decision
