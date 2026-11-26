"""Unit tests for the deterministic part of M1 (no model calls).

These test that the implementation matches the specification in docs/M1_DESIGN.md section 7.
They do not show that the specification is right; that needs the template and replay sets.
"""
from cdv.m1 import (ACCEPT, PENDING, REJECT, UNDETERMINED, ChangeOp, Entry, Ledger, UserTurn,
                    check_change, check_conflicts, check_grounding, check_preservation,
                    check_substitute, gate_hint, scan_omissions, verify_turn)

T1 = UserTurn("u1", 0, "Please get me ANC headphones from Sony under $300.")
T2 = UserTurn("u2", 4, "Actually I can go up to $350.")
T3 = UserTurn("u3", 8, "I'll go with the helmet.")
T4 = UserTurn("u4", 10, "If the Sony is out of stock, Bose is fine.")
T5 = UserTurn("u5", 12, "Or the closest thing to it if it's out of stock.")
TURNS = {t.turn_id: t for t in (T1, T2, T3, T4, T5)}

BUDGET = Entry("b", "budget_max", 300, basis=("u1",))
BRAND = Entry("br", "brand_in", ("Sony",), basis=("u1",))
BUNDLE = Entry("it", "bundle_all", ("helmet", "sensor"), basis=("u0",))
PREV = Ledger(1, (BUDGET, BRAND))


# ---- V-P preservation
def test_vp_unexplained_loss_is_rejected():
    new = Ledger(2, (BRAND,))
    f = check_preservation(PREV, new, accepted=[])
    assert f.status == REJECT and f.codes == ["LOST:b"]


def test_vp_explained_change_passes():
    op = ChangeOp("relax", "b", Entry("b", "budget_max", 350, basis=("u2",)), ("u2",))
    new = Ledger(2, (Entry("b", "budget_max", 350, basis=("u2",)), BRAND))
    assert check_preservation(PREV, new, [op]).status == ACCEPT


def test_vp_silent_value_change_is_rejected():
    new = Ledger(2, (Entry("b", "budget_max", 500, basis=("u1",)), BRAND))
    assert check_preservation(PREV, new, []).codes == ["CHANGED:b"]


# ---- V-B grounding and omission
def test_vb_value_must_be_stated_in_basis():
    assert check_grounding(Entry("b", "budget_max", 300, basis=("u1",)), TURNS).status == ACCEPT
    assert check_grounding(Entry("b", "budget_max", 500, basis=("u1",)), TURNS).codes == ["VALUE_NOT_STATED"]


def test_vb_non_user_basis_is_rejected():
    assert check_grounding(Entry("b", "budget_max", 300, basis=("seller:listing-3",)), TURNS).codes == ["NO_USER_BASIS"]


def test_vb_free_text_goes_to_nli_stage():
    assert check_grounding(Entry("p", "pref:comfort", "most important", basis=("u1",)), TURNS).status == UNDETERMINED


def test_vb_omission_scan_reads_all_user_turns():
    # The extractor kept the old budget although the user stated a new one later.
    f = scan_omissions(PREV, [T1, T2])
    assert f.status == PENDING and f.codes == ["OMITTED_BUDGET:u2"]
    f2 = scan_omissions(PREV, [T1, T4])
    assert "OMITTED_SUBSTITUTE:u4" in f2.codes


# ---- V-C legitimate change (asymmetric)
def test_vc_explicit_relax_is_accepted():
    op = ChangeOp("relax", "b", Entry("b", "budget_max", 350, basis=("u2",)), ("u2",))
    assert check_change(op, PREV, TURNS).status == ACCEPT


def test_vc_relax_citing_seller_text_is_rejected():
    op = ChangeOp("relax", "b", Entry("b", "budget_max", 500, basis=("seller:x",)), ("seller:x",))
    assert check_change(op, PREV, TURNS).codes == ["NON_USER_SOURCE"]


def test_vc_relax_to_unstated_value_is_pending():
    op = ChangeOp("relax", "b", Entry("b", "budget_max", 400, basis=("u2",)), ("u2",))
    assert check_change(op, PREV, TURNS).codes == ["WIDEN_VALUE_NOT_STATED"]


def test_vc_ambiguous_pick_does_not_revoke_hard_bundle():
    prev = Ledger(1, (BUNDLE,))
    # CartTrace pattern: "I'll go with the helmet" turned into dropping a required bundle member.
    op = ChangeOp("override", "it", Entry("it", "bundle_all", ("helmet",), basis=("u3",)), ("u3",))
    op_revoke = ChangeOp("revoke", "it", None, ("u3",))
    assert check_change(op, prev, TURNS).codes == ["AMBIGUOUS_PICK_NOT_REVOCATION"]
    assert check_change(op_revoke, prev, TURNS).codes == ["AMBIGUOUS_PICK_NOT_REVOCATION"]
    # an any-of list narrowed to one item is a real narrowing
    anyof = Ledger(1, (Entry("ia", "item_in", ("helmet", "sensor"), basis=("u1",)),))
    op2 = ChangeOp("override", "ia", Entry("ia", "item_in", ("helmet",), basis=("u3",)), ("u3",))
    assert check_change(op2, anyof, TURNS).status == ACCEPT


def test_vc_tightening_with_stated_value_is_accepted():
    t = {"u9": UserTurn("u9", 20, "Keep it under 200 please.")}
    op = ChangeOp("tighten", "b", Entry("b", "budget_max", 200, basis=("u9",)), ("u9",))
    assert check_change(op, PREV, t).status == ACCEPT


# ---- V-X conflicts
def test_vx_two_budgets_conflict_until_resolved():
    led = Ledger(2, (BUDGET, Entry("b2", "budget_max", 350, basis=("u2",)), BRAND))
    assert check_conflicts(led, TURNS).codes == ["BUDGET_MAX_MULTIPLE:b,b2"]


def test_vx_brand_in_out_conflict():
    led = Ledger(2, (BRAND, Entry("bo", "brand_out", ("Sony",), basis=("u2",))))
    assert check_conflicts(led, TURNS).codes == ["BRAND_IN_OUT:br,bo"]


def test_vx_no_conflict():
    assert check_conflicts(PREV, TURNS).status == ACCEPT


# ---- V-S conditional substitution
def _sub(scope, basis=("u4",)):
    return Entry("s", "substitute", None, basis=basis, scope=scope)


def test_vs_named_alternative_inherits_budget():
    s = _sub({"named": True, "then": {"brand_in": ["Bose"], "budget_max": 300}})
    assert check_substitute(s, Ledger(2, PREV.entries + (s,)), TURNS).status == ACCEPT


def test_vs_then_that_drops_budget_is_rejected():
    s = _sub({"named": True, "then": {"brand_in": ["Bose"], "budget_max": None}})
    assert check_substitute(s, Ledger(2, PREV.entries + (s,)), TURNS).codes == ["THEN_DROPS_BUDGET:b"]


def test_vs_unstated_alternative_is_rejected():
    s = _sub({"named": True, "then": {"brand_in": ["JBL"], "budget_max": 300}})
    assert "THEN_NAMES_UNSTATED_ALTERNATIVE" in check_substitute(s, Ledger(2, PREV.entries + (s,)), TURNS).codes


def test_vs_closest_thing_keeps_product_type_and_cannot_add_brands():
    pt = Entry("pt", "product_type", "headphones", basis=("u1",))
    s = _sub({"named": False, "then": {"product_type": "headphones", "budget_max": 300}}, basis=("u5",))
    assert check_substitute(s, Ledger(2, (BUDGET, pt, s)), TURNS).status == ACCEPT
    s2 = _sub({"named": False, "then": {"product_type": "earbuds", "budget_max": 300,
                                         "brand_in": ["Bose"]}}, basis=("u5",))
    codes = check_substitute(s2, Ledger(2, (BUDGET, pt, s2)), TURNS).codes
    assert "THEN_DROPS_PRODUCT_TYPE:pt" in codes and "CLOSEST_THING_WITH_BRAND_WIDENING" in codes


def test_vs_clause_without_user_conditional_is_rejected():
    s = _sub({"named": True, "then": {"brand_in": ["Bose"], "budget_max": 300}}, basis=("u3",))
    assert check_substitute(s, Ledger(2, PREV.entries + (s,)), TURNS).codes == ["NO_CONDITIONAL_CUE"]


# ---- driver: selective application and gate hint
def test_driver_applies_only_verified_ops_and_keeps_rest():
    ops = [ChangeOp("relax", "b", Entry("b", "budget_max", 350, basis=("u2",)), ("u2",)),
           ChangeOp("revoke", "br", None, ("seller:x",))]
    r = verify_turn(PREV, ops, [T1, T2])
    led = r.ledger.by_id()
    assert led["b"].value == 350 and "br" in led           # relax applied, seller revoke ignored
    assert [f.codes for f in r.change_findings][1] == ["NON_USER_SOURCE"]
    assert gate_hint(r) == "OK"


def test_driver_pending_change_means_clarify():
    ops = [ChangeOp("revoke", "it", None, ("u3",))]
    r = verify_turn(Ledger(1, (BUNDLE,)), ops, [T3])
    assert "it" in r.ledger.by_id() and gate_hint(r) == "CLARIFY"


# ---- omission scan: extended fields (2026-11-26)
def _turns(*texts):
    return [UserTurn(f"u{i}", i, s) for i, s in enumerate(texts)]


def test_omission_quantity_latest_wins():
    led = Ledger(1, (Entry("q", "quantity", 2, basis=("u0",)),))
    assert scan_omissions(led, _turns("I'd like 2.")).status == ACCEPT
    assert scan_omissions(led, _turns("I'd like 2.", "Actually make it 3.")).codes == ["OMITTED_QUANTITY:u1"]


def test_omission_quantity_ignores_numbers_in_titles():
    assert scan_omissions(Ledger(1, ()), _turns("I want the 24CT Prismacolor pencils")).status == ACCEPT


def test_omission_brand_in_and_out_need_known_brands():
    led = Ledger(1, ())
    f = scan_omissions(led, _turns("Only Sony please.", "No Bose."), known_brands=("Sony", "Bose"))
    assert f.codes == ["OMITTED_BRAND_IN:u0:Sony", "OMITTED_BRAND_OUT:u1:Bose"]
    assert scan_omissions(led, _turns("Only Sony please."), known_brands=()).status == ACCEPT


def test_omission_bundle_required_items():
    items = {"p1": "keyboard stand", "p2": "tongue drum"}
    led = Ledger(1, ())
    f = scan_omissions(led, _turns("I want the keyboard stand and the tongue drum together."), known_items=items)
    assert f.codes == ["OMITTED_BUNDLE:u0"]
    ok = Ledger(1, (Entry("b", "bundle_all", ("p1", "p2"), basis=("u0",)),))
    assert scan_omissions(ok, _turns("I want the keyboard stand and the tongue drum together."), known_items=items).status == ACCEPT


def test_omission_deadline_and_fulfillment():
    f = scan_omissions(Ledger(1, ()), _turns("It needs to arrive within 3 days.", "I'll collect it from the store."))
    assert f.codes == ["OMITTED_DEADLINE:u0", "OMITTED_FULFILLMENT:u1:pickup"]
    led = Ledger(1, (Entry("d", "deadline_days", 3, basis=("u0",)), Entry("f", "fulfillment", "pickup", basis=("u1",))))
    assert scan_omissions(led, _turns("It needs to arrive within 3 days.", "I'll collect it from the store.")).status == ACCEPT


def test_omission_fulfillment_latest_statement():
    led = Ledger(1, (Entry("f", "fulfillment", "pickup", basis=("u0",)),))
    f = scan_omissions(led, _turns("I'll pick it up.", "Actually please ship it to my office."))
    assert f.codes == ["OMITTED_FULFILLMENT:u1:ship"]


# Rule gaps found on the real walkthrough case ep-b63223f61e0a (validation), 2026-11-26.
def test_collect_in_store_is_pickup():
    from cdv import m1
    assert [k for _, k in m1.fulfillment_mentions("I'd rather collect it in store.")] == ["pickup"]


def test_tell_me_if_out_of_stock_is_not_a_substitution_allowance():
    from cdv import m1
    assert not m1.CONDITIONAL_RE.search("No preference on the color. If it is out of stock, just tell me.")
    assert m1.CONDITIONAL_RE.search("If it is out of stock, the closest one is fine.")
