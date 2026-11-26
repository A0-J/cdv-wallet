"""M1 v2 + integrated pipeline: unit tests (synthetic) and data-reading tests (skipped without C:/ct)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval" / "integrated"))

from cdv import verdict
from cdv.m1 import Entry, UserTurn
from cdv.v2.candidates import Registry, resolve_turn
from cdv.v2.integrate import decide_selective, scope_from
from cdv.v2.m1v2 import Ctx, Unresolved, qty_anchor, run_m1v2
from cdv.v2.scope import LineV2, ScopeV2

PC, SP = "set_purchase_conditions", "set_substitution_policy"


def reg_with(*products, seq=1):
    r = Registry()
    res = {"products": [{"id": pid, "title": title, "metadata": {"brand": brand} if brand else {},
                         "variants": [{"id": pid + "v", "price": {"amount": int(price * 100)}, "title": title,
                                       "availability": {"available": True}}]} for pid, title, brand, price in products]}
    r.add_tool_result(seq, "search_catalog", json.dumps(res))
    return r


def line(cid, price, brand=None, title="", known=True, pid=None):
    return LineV2("s", cid, price, 1, brand, pid, frozenset(), title=title, kind_text=title, product_id=pid,
                  brand_known=known and brand is not None)


# ---------------------------------------------------------------- common decision function

def test_plan_v3_precedence_clarify_over_m2a_deny():
    assert verdict.plan_v3("CLARIFY", "DENY") == "CLARIFY"
    assert verdict.plan_v3(None, "DENY") == "DENY"
    assert verdict.plan_v3("OK", "ALLOW") == "ALLOW"


def test_integrated_base_failure_is_never_overridden():
    assert verdict.integrated("DENY", ["MANDATE_SIG"], m1_asks=True) == "DENY"
    assert verdict.integrated("DENY", ["AVIP_V2"], m1_asks=True) == "DENY"
    assert verdict.integrated("DENY", ["OUT_OF_SCOPE"], m1_asks=True) == "CLARIFY"
    assert verdict.integrated("ALLOW", [], m1_asks=False) == "ALLOW"


# ---------------------------------------------------------------- Scope v2: unknown is not a violation

def test_missing_brand_is_unknown_not_violation():
    s = ScopeV2(brands=frozenset({"Sony"}))
    l = line("a", 10, brand=None, title="Wireless Headphones")
    assert s.violations([l]) == []
    assert s.unknowns([l]) == ["UNKNOWN_ATTR:brand:a"]


def test_brand_decided_from_title_or_field():
    s = ScopeV2(brands=frozenset({"Sony"}), brands_excluded=frozenset({"Bose"}))
    assert s.violations([line("a", 10, brand=None, title="Sony WH-1000")]) == []
    assert s.unknowns([line("a", 10, brand=None, title="Sony WH-1000")]) == []
    assert "BRAND:b" in s.violations([line("b", 10, brand="Anker", title="Anker Q30")])
    assert "BRAND_EXCLUDED:c" in ScopeV2(brands_excluded=frozenset({"Bose"})).violations([line("c", 10, "Bose", "Bose QC")])


def test_selection_empty_allows_any_product_within_C_but_not_outside():
    s_empty = ScopeV2(max_total=50, cart_ids=None)
    assert s_empty.violations([line("x", 40)]) == []
    assert s_empty.violations([line("x", 60)]) == ["MAX_TOTAL"]
    s_set = ScopeV2(max_total=50, cart_ids=frozenset({"p1", "p1v"}))
    assert s_set.violations([line("p2v", 40, pid="p2")]) == ["ITEM:p2v"]
    assert s_set.violations([line("p1v", 40, pid="p1")]) == []


def test_gate_unknown_attr_gives_clarify():
    sys.path.insert(0, str(ROOT))
    from adapters import avip
    from cdv.canon import new_signing_key, public_of
    from cdv.gate import Request, authorize, combined_hash, context_record
    from cdv.mandate import Mandate, VersionRegistry
    sk = new_signing_key()
    offers = [{"cart_id": "a", "seller": "s", "label": "Wireless Headphones", "amount": "10.00", "currency": "USD"}]
    cat = {("s", "a"): line("a", 10, brand=None, title="Wireless Headphones")}
    for scope, want in ((ScopeV2(brands=frozenset({"Sony"})), "CLARIFY"), (ScopeV2(max_total=5), "DENY"),
                        (ScopeV2(max_total=50), "ALLOW")):
        m = Mandate("m", 1, scope, session="x").signed(sk)
        vr = VersionRegistry()
        vr.publish("m", 1)
        cap = avip.capture(offers)
        r = avip.record(cap, ("s", "a")).body
        c_r = context_record(m, None, [])
        res = authorize(Request(m, public_of(sk), vr, "x", offers, cat, [(("s", "a"), 1)], r, c_r,
                                combined_hash(avip.record_hash(r), c_r)))
        assert res.decision == want, (scope, res)


# ---------------------------------------------------------------- M1 v2

def test_quantity_anchor_needs_context():
    assert not qty_anchor(1, "Ship it to 1 Maple Way please")
    assert not qty_anchor(1, "I'll go with option 1")
    assert qty_anchor(2, "I need 2 bottles of it")
    assert qty_anchor(3, "three pairs please")


def _states(*pcs):
    return [{"seq": 2 * i, "state": {PC: pc}} for i, pc in enumerate(pcs)]


def _turns(*texts):
    return [UserTurn(f"s{2 * i}", 2 * i, t) for i, t in enumerate(texts)]


def test_non_user_source_rejected_not_found_kept_unresolved():
    reg = reg_with(("p1", "Sony WH-1000 Headphones", "Sony", 120.0))
    # agent says $135.58; extractor copies it as budget: NON_USER_SOURCE
    r = run_m1v2(_states({"budget_max": 100}, {"budget_max": 135.58}), _turns("Headphones under $100", "ok"),
                 [(1, "Your cart total is $135.58.")], reg, t=10)
    assert ("budget", "NON_USER_SOURCE") in r.rejected and r.ctx.entries["budget"].value == 100
    # value found nowhere: NOT_FOUND, not applied, kept as an unresolved item
    r2 = run_m1v2(_states({"budget_max": 100}, {"budget_max": 180}), _turns("Headphones under $100", "ok"), [], reg, t=10)
    assert r2.ctx.entries["budget"].value == 100
    assert any(u.id == "budget" and u.kind == "NOT_FOUND" for u in r2.unresolved)


def test_dropped_condition_without_cue_is_kept_and_explicit_revoke_applies():
    reg = reg_with(("p1", "Sony Headphones", "Sony", 50.0))
    r = run_m1v2(_states({"budget_max": 100}, {}), _turns("under $100", "the second one looks nice"), [], reg, t=10)
    assert r.ctx.entries["budget"].value == 100 and ("budget", "DROPPED_WITHOUT_CUE") in r.rejected
    r2 = run_m1v2(_states({"budget_max": 100}, {}), _turns("under $100", "Actually forget about the budget"), [], reg, t=10)
    assert "budget" not in r2.ctx.entries


def test_pick_within_constraints_sets_selection_without_asking():
    reg = reg_with(("p1", "Sony WH-1000 Wireless Headphones", "Sony", 80.0),
                   ("p2", "Bose QuietComfort Wireless Headphones", "Bose", 90.0))
    agent = [(1, "Here are two options:\n1. Sony WH-1000 Wireless Headphones $80\n2. Bose QuietComfort Wireless Headphones $90")]
    r = run_m1v2(_states({"budget_max": 100, "product_type": "headphones"},
                         {"budget_max": 100, "product_type": "Bose QuietComfort Wireless Headphones"}),
                 _turns("I need headphones under $100", "I'll go with option 2"), agent, reg, t=10)
    assert r.ctx.selection == frozenset({"p2"}) and r.selection_how == "list_index"
    assert r.ctx.kind == "headphones"                          # the specific name did not become a constraint
    assert not [u for u in r.unresolved if u.kind != "OMISSION"]


def test_agent_proposal_alone_does_not_select():
    reg = reg_with(("p1", "Sony WH-1000 Wireless Headphones", "Sony", 80.0))
    res = resolve_turn("What about the warranty?", "I recommend the Sony WH-1000 Wireless Headphones.", 5, reg)
    assert res.status == "NONE"
    res2 = resolve_turn("Sounds good", "I recommend the Sony WH-1000 Wireless Headphones.", 5, reg)
    assert res2.status == "RESOLVED"        # agreement to a single proposal (limit: see M1_V2_DESIGN 12.4)


def test_selective_reconfirmation_considers_interactions():
    # two unresolved items; each alone keeps the decision, together they change it -> must ask
    base = Ctx({}, None, None)
    a = Unresolved("a", "NOT_FOUND", [], [("no", lambda c: c), ("yes", lambda c: c.copy(kind=(c.kind or "") + "A"))])
    b = Unresolved("b", "NOT_FOUND", [], [("no", lambda c: c), ("yes", lambda c: c.copy(kind=(c.kind or "") + "B"))])
    gate = lambda c: ("DENY", ["X"]) if c.kind and "A" in c.kind and "B" in c.kind else ("ALLOW", [])  # noqa: E731
    d, codes, rel, n, approx = decide_selective(base, [a, b], gate)
    assert d == "CLARIFY" and set(rel) == {"a", "b"} and n == 4 and not approx
    gate2 = lambda c: ("ALLOW", [])  # noqa: E731
    assert decide_selective(base, [a, b], gate2)[0] == "ALLOW"


def test_scope_from_selection_includes_variants():
    reg = reg_with(("p1", "Sony Headphones", "Sony", 50.0))
    s = scope_from(Ctx({"budget": Entry("budget", "budget_max", 60.0)}, None, frozenset({"p1"})), reg)
    assert s.cart_ids == frozenset({"p1", "p1v"}) and s.max_total == 60.0


def test_m1v2_refuses_input_after_decision_point():
    with pytest.raises(AssertionError):
        run_m1v2(_states({"budget_max": 10}), _turns("x"), [], Registry(), t=0)


# ---------------------------------------------------------------- env input checks and split reading

def test_env_stops_on_empty_cart():
    import env as E
    T = [{"seq": 0, "actor": "shopper", "kind": "message", "text": "hi", "tool": None, "stage": "browse", "result": None}]
    with pytest.raises(E.InputError):
        E.build_case("ep-x", {"final_cart": "{}", "outcome_class": "RIGHT", "hidden_spec": "{}", "split": "validation"}, T)


DATA = Path(r"C:/ct/kit/dataset/data")


@pytest.mark.skipif(not DATA.exists(), reason="CartTrace data not present")
def test_reading_from_every_split_and_stop_on_missing():
    import glob

    import pyarrow.parquet as pq

    import env as E
    picks = {}
    for s in E.SPLITS:
        f = sorted(glob.glob(str(DATA / "messages" / "*" / f"{s}-*.parquet")))[0]
        picks[s] = pq.read_table(f, columns=["episode_id"]).to_pylist()[0]["episode_id"]
    msgs, turns = E.load_rows(set(picks.values()))
    for s, e in picks.items():
        assert msgs[e]["split"] == s and turns[e], s
    with pytest.raises(E.InputError):
        E.load_rows({picks["validation"], "ep-does-not-exist"})


def test_pick_in_bundle_does_not_exclude_other_members():
    # found on validation pilot ep-535246e7fd35 (functional test, 2026-11-26)
    reg = reg_with(("p1", "Microfiber Sheet Set", None, 30.0), ("p2", "Towel Set", None, 20.0))
    ctx = Ctx({"bundle": Entry("bundle", "bundle_all", ("sheet set", "towel set"))}, None, frozenset({"p1"}))
    s = scope_from(ctx, reg)
    assert s.cart_ids is None and s.must_include == (frozenset({"p1", "p1v"}),)
    both = [line("p1v", 30, title="Microfiber Sheet Set", pid="p1"), line("p2v", 20, title="Towel Set", pid="p2")]
    assert s.violations(both) == []
    assert s.violations([line("p2v", 20, title="Towel Set", pid="p2"), line("x", 5, title="Pillow")]) == ["SELECTED_MISSING:p1"]


@pytest.mark.skipif(not DATA.exists(), reason="CartTrace data not present")
def test_plan_v3_pilot_rows_reproduce_exactly():
    """Quick form of eval/regress/reproduce_plan_v3.py (full run: 666 rows, all exact on 2026-11-26)."""
    sys.path.insert(0, str(ROOT / "eval" / "regress"))
    import reproduce_plan_v3 as RP
    from cdv.nli import NLI
    res = RP.reproduce_set("R1_validation", NLI())
    assert res["mismatched_rows"] == 0 and res["n_verdict_mismatches"] == 0, res


def test_brand_title_match_counts_even_if_brand_field_is_store_name():
    # dev finding: 'Tide' product whose brand field is the store 'Builtamart'
    s = ScopeV2(brands=frozenset({"Tide"}))
    assert s.violations([line("a", 6.49, brand="Builtamart", title="Tide Ultra Original Scent Bar Detergent")]) == []
    assert s.violations([line("b", 6.49, brand="Builtamart", title="Generic Bar Detergent")]) == ["BRAND:b"]


def test_g1v2_scoring_multi_change_and_preservation():
    sys.path.insert(0, str(ROOT / "eval" / "g1v2"))
    import run_g1v2 as G
    case = {"type": "L2", "dialogue": [{"role": "user", "text": "Shoes under $30", "turn_id": "s0"},
                                       {"role": "assistant", "text": "Got it.", "turn_id": "s1"},
                                       {"role": "user", "text": "Please keep it under $24.", "turn_id": "s2"},
                                       {"role": "assistant", "text": "Understood.", "turn_id": "s3"},
                                       {"role": "user", "text": "Actually I can go up to $40.", "turn_id": "s4"}],
            "gold": {"final": {"budget_max": 40}, "per_user_turn": [{"budget_max": 30}, {"budget_max": 24}, {"budget_max": 40}],
                     "expect_no_question": True}}
    fn = [{"turn_id": t, "selected": [], "state": {PC: {"budget_max": b}}} for t, b in (("s0", 30), ("s2", 24), ("s4", 40))]
    out = G.evaluate(case, fn, {"state": {PC: {"budget_max": 40}}}, None)
    assert out["fnctod"]["final_ok"] and out["fnctod"]["steps_ok"]
    assert out["fnctod_r"]["final_ok"] and out["fnctod_r"]["steps_ok"] and not out["fnctod_r"]["unnecessary_question"]
    # a pick that the extractor turns into a budget raise must not count as preserved
    case2 = {"type": "S2", "dialogue": case["dialogue"][:1] + [{"role": "assistant", "text": "1. A - $20\n2. B - $39", "turn_id": "s1"},
                                                              {"role": "user", "text": "I'll go with option 2.", "turn_id": "s2"}],
             "gold": {"final": {"budget_max": 30}, "per_user_turn": [{"budget_max": 30}, {"budget_max": 30}], "expect_no_question": False}}
    fn2 = [{"turn_id": "s0", "selected": [], "state": {PC: {"budget_max": 30}}}, {"turn_id": "s2", "selected": [], "state": {PC: {"budget_max": 39}}}]
    out2 = G.evaluate(case2, fn2, {"state": {PC: {"budget_max": 39}}}, None)
    assert out2["fnctod"]["preserved"] is False and out2["fnctod_r"]["preserved"] is True


def test_checkout_violations_at_consent():
    from cdv.v2.scope import checkout_violations
    s = ScopeV2(fulfillment="pickup", deadline_days=5)
    assert checkout_violations(s, {"fulfillment": "ship", "max_days": 3}) == (["FULFILLMENT:ship"], [])
    assert checkout_violations(s, {"fulfillment": "pickup", "max_days": 7}) == (["DEADLINE:7>5"], [])
    assert checkout_violations(s, {}) == ([], ["fulfillment", "deadline_days"])     # unverified, not satisfied
    assert checkout_violations(ScopeV2(), {"fulfillment": "ship"}) == ([], [])


def test_checkout_facts_reads_selected_option_only():
    import env as E
    res = {"fulfillment": {"methods": [{"type": "shipping", "groups": [{"options": [
        {"id": "std", "title": "Standard (4-7 days)"}, {"id": "exp", "title": "Express (1-2 days)"}], "selected_option_id": "exp"}]}]}}
    T = [{"seq": 5, "kind": "tool_result", "tool": "update_checkout", "result": json.dumps(json.dumps(res))}]
    assert E.checkout_facts(T, 10) == {"fulfillment": "ship", "max_days": 2}
    res2 = {"fulfillment": {"methods": [{"type": "shipping", "groups": [{"options": [{"id": "std", "title": "Standard (4-7 days)"}]}]}]}}
    T2 = [{"seq": 5, "kind": "tool_result", "tool": "update_checkout", "result": json.dumps(res2)}]
    assert E.checkout_facts(T2, 10) == {"fulfillment": "ship", "max_days": None}   # offered, not selected


def test_joint_pending_items_counterexample_through_real_scope():
    """Plan section 2 counterexample: each pending change alone keeps DENY, only both together give ALLOW.
    An individual-only check would never ask; the joint check must ask (CLARIFY naming both)."""
    reg = reg_with(("p1", "Bose QC Headphones", "Bose", 150.0))
    base = Ctx({"brand_in": Entry("brand_in", "brand_in", ("Sony",)), "budget": Entry("budget", "budget_max", 100.0)}, None, None)
    u1 = Unresolved("u1", "C_PENDING", [], [("kept", lambda c: c),
                                           ("bose_ok", lambda c: Ctx({**c.entries, "brand_in": Entry("brand_in", "brand_in", ("Sony", "Bose"))}, c.kind, c.selection))])
    u2 = Unresolved("u2", "C_PENDING", [], [("kept", lambda c: c),
                                           ("budget_200", lambda c: Ctx({**c.entries, "budget": Entry("budget", "budget_max", 200.0)}, c.kind, c.selection))])
    cart = [line("p1v", 150.0, brand="Bose", title="Bose QC Headphones", pid="p1")]
    gate = lambda c: (("DENY", scope_from(c, reg).violations(cart)) if scope_from(c, reg).violations(cart) else ("ALLOW", []))  # noqa: E731
    assert gate(base)[0] == "DENY"
    assert gate(u1.variants[1][1](base))[0] == "DENY" and gate(u2.variants[1][1](base))[0] == "DENY"   # each alone
    assert gate(u2.variants[1][1](u1.variants[1][1](base)))[0] == "ALLOW"                              # only jointly
    d, codes, rel, n, approx = decide_selective(base, [u1, u2], gate)
    assert d == "CLARIFY" and set(rel) == {"u1", "u2"} and n == 4 and not approx
