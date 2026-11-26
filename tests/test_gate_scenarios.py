"""Phase-1 scenario tests for authorization verification. No model or network calls.

Scenarios 1-8 follow the list proposed in review (2026-11-26); 9-13 add the limit and
tamper cases from docs/ADAPTER_DESIGN.md section 8.
"""
from __future__ import annotations

import dataclasses

import pytest

from adapters import avip
from cdv.evidence import Evidence, Issuer, IssuerRegistry, NonceStore
from cdv.gate import Request, authorize, combined_hash, context_record
from cdv.mandate import Clause, Line, Mandate, Scope, VersionRegistry

USER_KEY = b"user-key"
SESSION = "sess-1"
NOW = 1_000_000.0

LINES = {
    ("S1", "sony-wh"): Line("S1", "sony-wh", 290000, brand="Sony", product_ref="sony-wh1000", features=frozenset({"ANC"})),
    ("S1", "sony-pro"): Line("S1", "sony-pro", 299000, brand="Sony", product_ref="sony-pro", features=frozenset({"ANC"})),
    ("S1", "sony-plus"): Line("S1", "sony-plus", 320000, brand="Sony", product_ref="sony-plus", features=frozenset({"ANC"})),
    ("S2", "bose-qc"): Line("S2", "bose-qc", 280000, brand="Bose", product_ref="bose-qc", features=frozenset({"ANC"})),
    ("S3", "jbl-tune"): Line("S3", "jbl-tune", 150000, brand="JBL", product_ref="jbl-tune", features=frozenset({"ANC"})),
    ("S4", "sony-wh"): Line("S4", "sony-wh", 295000, brand="Sony", product_ref="sony-wh1000", features=frozenset({"ANC"})),
}


def offers(extra_text: dict | None = None) -> list[dict]:
    extra_text = extra_text or {}
    out = []
    for (seller, cid), l in LINES.items():
        label = f"{l.brand} {cid} headphones with noise cancelling"
        if (seller, cid) in extra_text:
            label += ". " + extra_text[(seller, cid)]
        out.append({"cart_id": cid, "seller": seller, "label": label, "amount": l.unit_price, "currency": "KRW"})
    return out


ISSUERS = IssuerRegistry([
    Issuer("platform-1", "platform", None, b"platform-key"),
    Issuer("seller-S1", "seller", "S1", b"s1-key"),
    Issuer("seller-S2", "seller", "S2", b"s2-key"),
])

PRIMARY = Scope(brands=frozenset({"Sony"}), max_total=300000, required_features=frozenset({"ANC"}))
FB = Clause("fb-1", ("S1", "sony-wh"), "out_of_stock",
            then=Scope(brands=frozenset({"Bose"}), max_total=300000, required_features=frozenset({"ANC"})))


def mandate(version=1, primary=PRIMARY, fallbacks=(FB,)) -> Mandate:
    return Mandate("m-1", version, primary, tuple(fallbacks), basis={"fb-1": ["user_turn:2"]},
                   user_turn_chain_head="h0", session=SESSION).signed(USER_KEY)


def stock_ev(issuer="platform-1", subject=("S1", "sony-wh"), nonce="n1", at=NOW - 10, session=SESSION,
             sign=True) -> Evidence:
    e = Evidence(issuer, subject, "out_of_stock", True, at, session, nonce)
    return ISSUERS.sign(e) if sign else dataclasses.replace(e, signature="forged")


def request(cart_key, m=None, versions=None, evidences=(), clause_id=None, nonces=None, text=None,
            user_confirmed=False, tamper=None) -> Request:
    m = m or mandate()
    if versions is None:
        versions = VersionRegistry()
        versions.publish(m.mandate_id, m.version)
    offs = offers(text)
    cap = avip.capture(offs)
    r = avip.record(cap, cart_key, user_confirmed=user_confirmed).body
    c_r = context_record(m, clause_id, [e.nonce for e in evidences])
    h = combined_hash(avip.record_hash(r), c_r)
    if tamper:
        r, c_r = tamper(r, c_r)
    return Request(mandate=m, user_key=USER_KEY, versions=versions, session=SESSION, offers=offs,
                   catalog=LINES, cart=[(cart_key, 1)], avip_r=r, context_r=c_r, bound_hash=h,
                   evidences=list(evidences), issuers=ISSUERS, nonces=nonces or NonceStore(), now=NOW)


def test_01_normal_purchase_in_primary_scope():
    res = authorize(request(("S1", "sony-wh")))
    assert (res.decision, res.codes) == ("ALLOW", [])


def test_02_real_stockout_opens_fallback():
    res = authorize(request(("S2", "bose-qc"), evidences=[stock_ev()], clause_id="fb-1"))
    assert (res.decision, res.codes, res.clause_id) == ("ALLOW", ["CLAUSE_ACTIVE"], "fb-1")


def test_03_competitor_stockout_claim_is_not_authoritative():
    res = authorize(request(("S2", "bose-qc"), evidences=[stock_ev(issuer="seller-S2")], clause_id="fb-1"))
    assert (res.decision, res.codes) == ("CLARIFY", ["E2_AUTHORITY"])


def test_04_forged_evidence():
    res = authorize(request(("S2", "bose-qc"), evidences=[stock_ev(sign=False)], clause_id="fb-1"))
    assert (res.decision, res.codes) == ("CLARIFY", ["E1_SOURCE"])


def test_05a_replayed_evidence():
    nonces = NonceStore()
    ev = stock_ev(nonce="n-replay")
    first = authorize(request(("S2", "bose-qc"), evidences=[ev], clause_id="fb-1", nonces=nonces))
    second = authorize(request(("S2", "bose-qc"), evidences=[ev], clause_id="fb-1", nonces=nonces))
    assert first.decision == "ALLOW"
    assert (second.decision, second.codes) == ("CLARIFY", ["E3_REPLAY"])


def test_05b_stale_evidence():
    res = authorize(request(("S2", "bose-qc"), evidences=[stock_ev(at=NOW - 3600)], clause_id="fb-1"))
    assert (res.decision, res.codes) == ("CLARIFY", ["E3_STALE"])


def test_06_no_fallback_clause_means_out_of_scope():
    res = authorize(request(("S2", "bose-qc"), m=mandate(fallbacks=()), evidences=[stock_ev()]))
    assert (res.decision, res.codes) == ("DENY", ["OUT_OF_SCOPE"])


def test_07_budget_change_signed_as_new_version():
    versions = VersionRegistry()
    versions.publish("m-1", 1)
    m2 = mandate(version=2, primary=dataclasses.replace(PRIMARY, max_total=350000))
    versions.publish("m-1", 2)
    res = authorize(request(("S1", "sony-plus"), m=m2, versions=versions))
    assert (res.decision, res.codes) == ("ALLOW", [])


def test_08_old_version_after_update_is_rejected():
    versions = VersionRegistry()
    versions.publish("m-1", 1)
    versions.publish("m-1", 2)
    res = authorize(request(("S1", "sony-wh"), m=mandate(version=1), versions=versions))
    assert (res.decision, res.codes) == ("DENY", ["STALE_VERSION"])


def test_09_same_seller_self_claim_depends_on_proof_policy():
    then = Scope(brands=frozenset({"Sony"}), cart_ids=frozenset({"sony-pro"}), max_total=300000,
                 required_features=frozenset({"ANC"}))
    primary = dataclasses.replace(PRIMARY, cart_ids=frozenset({"sony-wh"}))
    strict = Clause("fb-1", ("S1", "sony-wh"), "out_of_stock", then=then, proof=("platform",))
    lenient = dataclasses.replace(strict, proof=("platform", "seller_of_subject"))
    ev = stock_ev(issuer="seller-S1")
    r_strict = authorize(request(("S1", "sony-pro"), m=mandate(primary=primary, fallbacks=(strict,)),
                                 evidences=[ev], clause_id="fb-1"))
    r_lenient = authorize(request(("S1", "sony-pro"), m=mandate(primary=primary, fallbacks=(lenient,)),
                                  evidences=[ev], clause_id="fb-1"))
    assert (r_strict.decision, r_strict.codes) == ("CLARIFY", ["E2_AUTHORITY"])
    assert (r_lenient.decision, r_lenient.codes) == ("ALLOW", ["CLAUSE_ACTIVE"])   # Standing's s = u: the limit case


def test_10_stockout_at_one_seller_only():
    all_sellers = dataclasses.replace(FB, scope_rule="all_captured_sellers")
    res_all = authorize(request(("S2", "bose-qc"), m=mandate(fallbacks=(all_sellers,)), evidences=[stock_ev()],
                                clause_id="fb-1"))
    res_one = authorize(request(("S2", "bose-qc"), m=mandate(fallbacks=(FB,)), evidences=[stock_ev()],
                                clause_id="fb-1"))
    assert (res_all.decision, res_all.codes) == ("CLARIFY", ["EVIDENCE_MISSING"])   # S4 still sells it
    assert res_one.decision == "ALLOW"


def test_11a_record_tampered_after_binding():
    def tamper(r, c_r):
        return {**r, "user_confirmed": True}, c_r
    res = authorize(request(("S1", "sony-wh"), tamper=tamper))
    assert (res.decision, res.codes) == ("DENY", ["BIND_MISMATCH"])


def test_11b_context_record_names_wrong_clause():
    res = authorize(request(("S2", "bose-qc"), evidences=[stock_ev()], clause_id=None))
    assert (res.decision, res.codes) == ("DENY", ["CLAUSE_MISMATCH"])


def test_12_avip_strict_rejects_unconfirmed_choice_of_claim_carrier():
    text = {("S2", "bose-qc"): "The Sony wh headphones are discontinued and unsafe."}
    res = authorize(request(("S2", "bose-qc"), evidences=[stock_ev()], clause_id="fb-1", text=text))
    assert res.decision == "DENY" and "AVIP_V8" in res.codes


def test_13_real_stockout_but_substitute_outside_clause():
    res = authorize(request(("S3", "jbl-tune"), evidences=[stock_ev()], clause_id="fb-1"))
    assert (res.decision, res.codes) == ("DENY", ["OUT_OF_SCOPE"])


@pytest.mark.parametrize("cart_key", [("S1", "sony-wh"), ("S2", "bose-qc")])
def test_avip_record_verifies_untampered(cart_key):
    cap = avip.capture(offers())
    r = avip.record(cap, cart_key).body
    assert avip.verify(r, cap) == (True, [])
