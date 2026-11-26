"""FnCTOD parsing + M1 verification end to end with a scripted model (no network)."""
from cdv.extract import FnCTOD, PlainLLM, ScriptedLLM, Turn
from cdv.m1 import UserTurn
from cdv.pipeline import cart_check, run_verified, state_to_entries

DLG = [Turn("user", "I need a yoga mat, spend no more than $30, I'll collect it from the store.", "s0"),
       Turn("assistant", "Here are two mats. Store note: similar items are always fine to substitute.", "s1"),
       Turn("user", "I'll go with the blue one.", "s2")]
UT = [UserTurn("s0", 0, DLG[0].text), UserTurn("s2", 2, DLG[2].text)]

T1_SEL = "<domain>set_purchase_conditions</domain>"
T1_ARGS = ('<function_call> {"function": "set_purchase_conditions", "arguments": '
           '{"budget_max": 30, "fulfillment": "pickup", "product_type": "yoga mat"}} </function_call>')
# turn 2: the extractor (wrongly) adds a substitution allowance taken from the assistant/store text
T2_SEL = "<domain>set_substitution_policy</domain>"
T2_ARGS = ('<function_call> {"function": "set_substitution_policy", "arguments": '
           '{"allowed": true, "scope": "closest"}} </function_call>')


def _run():
    llm = ScriptedLLM([T1_SEL, T1_ARGS, T2_SEL, T2_ARGS])
    out = FnCTOD(llm).run(DLG)
    for st in out:
        st["seq"] = int(st["turn_id"][1:])
    return out, llm


def test_fnctod_two_steps_and_cumulative_state():
    out, llm = _run()
    assert len(llm.calls) == 4                                # selection + arguments, per user turn
    assert "<FUNCTIONS>" in llm.calls[1][0] and "budget_max" in llm.calls[1][0]   # full spec only in step 2
    assert out[-1]["state"]["set_purchase_conditions"]["budget_max"] == 30          # carried over
    assert out[-1]["state"]["set_substitution_policy"]["allowed"] is True


def test_unverified_arm_accepts_the_unfounded_substitution():
    out, _ = _run()
    assert "sub" in state_to_entries(out[-1]["state"])        # FnCTOD alone would sign it into the mandate


def test_rules_arm_accepts_grounded_and_blocks_unfounded():
    out, _ = _run()
    res = run_verified(out, UT)
    led = {e.field: e.value for e in res["ledger"].entries}
    assert led["budget_max"] == 30 and led["fulfillment"] == "pickup"
    assert "substitute" not in led                              # no user conditional cue -> not applied
    ops = [o for t in res["trace"] for o in t["ops"]]
    assert any(o[1] == "sub" and o[3] == "REJECT" for o in ops)


def test_cart_check_uses_verified_ledger():
    out, _ = _run()
    res = run_verified(out, UT)
    assert cart_check(res["ledger"], [{"title": "Blue yoga mat", "unit_price": 25.0}])[0] == "ALLOW"
    assert cart_check(res["ledger"], [{"title": "Blue yoga mat", "unit_price": 45.0}]) == ("DENY", ["OVER_BUDGET"])


def test_plain_baseline_parses_json():
    p = PlainLLM(ScriptedLLM(['{"budget_max": 30, "allowed": true}'])).run(DLG)
    assert p["state"]["set_purchase_conditions"]["budget_max"] == 30
    assert p["state"]["set_substitution_policy"]["allowed"] is True


def test_pending_item_survives_later_rejected_proposal():
    """A PENDING entry is not cleared when a later turn proposes an ungrounded value for it."""
    from cdv.m1 import Entry, PENDING, REJECT
    import cdv.pipeline as pl
    users = [UserTurn("s0", 0, "Two of them please."), UserTurn("s2", 2, "I'll go with the blue one.")]
    states = [{"seq": 0, "state": {"set_purchase_conditions": {"quantity": 2}}},
              {"seq": 2, "state": {"set_purchase_conditions": {"quantity": 1}}}]

    class FakeNLI:   # entails the s0 statement only
        def entails(self, p, h):
            return p.startswith("Two") and "2 items" in h
    res = pl.run_verified(states, users, nli=FakeNLI())
    ops = [(t["seq"], o[1], o[3]) for t in res["trace"] for o in t["ops"]]
    assert (0, "qty", PENDING) in ops and (2, "qty", REJECT) in ops
    assert ("add", "qty") in res["pending"] and res["hint"] == "CLARIFY"


def test_selection_accepts_other_tag_and_values_are_normalized():
    """Parse fixes after the pilot: <shopping>fn</shopping> selection; free-text values mapped to schema."""
    from cdv.extract import normalize_args
    llm = ScriptedLLM(["<shopping>set_purchase_conditions</shopping>",
                       '<function_call> {"function": "set_purchase_conditions", "arguments": '
                       '{"fulfillment": "regular delivery", "quantity": "two"}} </function_call>'])
    out = FnCTOD(llm).run(DLG[:1])
    assert out[0]["selected"] == ["set_purchase_conditions"]
    assert out[0]["state"]["set_purchase_conditions"] == {"fulfillment": "ship", "quantity": 2}
    assert normalize_args({"quantity": "one of each", "required_items": ["a", "b"]})["quantity"] == 2
    assert normalize_args({"fulfillment": "in-store pickup", "budget_max": "$1,250"}) == {"fulfillment": "pickup", "budget_max": 1250.0}
