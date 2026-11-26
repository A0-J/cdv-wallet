"""Payment-request authority check (adjustment-history item 20, researcher decision 2026-11-27, before v4b was opened).

The payment request must match the payment grant it presents: grant id, payer, payee, currency, an amount within the
grant maximum, and an attempt time not after the grant expiry. Moved unchanged (same comparisons, same codes) from the
evaluation script eval/extdata/run_ext.py::authority_check. It runs BEFORE the authorization gate; cdv/gate.py::authorize,
the mandate signature format and the gate's decision order are unchanged. Any mismatch -> DENY with one code per field.
When no grant information exists for a payment (CartTrace has none) there is nothing to compare and nothing changes.
"""
from __future__ import annotations

from datetime import datetime


def _ts(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def check_payment_authority(payment_request: dict | None, grant: dict | None) -> list[str]:
    """Codes GRANT_GRANT_ID / GRANT_PAYER / GRANT_PAYEE / GRANT_CURRENCY / GRANT_AMOUNT / GRANT_EXPIRED; [] = consistent."""
    if not payment_request and not grant:
        return []
    pr, g = payment_request or {}, grant or {}
    bad = []
    for k in ("grant_id", "payer", "payee", "currency"):
        if pr.get(k) != g.get(k):
            bad.append(f"GRANT_{k.upper()}")
    if (pr.get("amount_minor") or 0) > (g.get("max_total_minor") or 0):
        bad.append("GRANT_AMOUNT")
    a, e = pr.get("attempt_at"), g.get("expires_at")
    if a and e:
        ta, te = _ts(a), _ts(e)
        if (ta > te) if (ta is not None and te is not None) else (str(a) > str(e)):
            bad.append("GRANT_EXPIRED")
    return bad


def apply(decision: str, codes: list, authority_codes: list | None) -> tuple[str, list]:
    """Pre-gate result applied to any configuration's decision: a mismatch gives DENY with the field codes."""
    if authority_codes:
        return "DENY", list(authority_codes)
    return decision, list(codes or [])
