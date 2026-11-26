"""Specs CONDITIONAL-1 and WIDEN-1 (cdv/m1.py). Sentences written from the definitions, not from any dataset."""
from cdv import m1

C, W, P = m1.CONDITIONAL_RE, m1.WIDEN_CUES, m1.PICK_ONLY


def test_conditional_needs_unavailability_condition_and_a_grant():
    for t in ("If the blue one is sold out, a similar one is fine.",
              "In case it's unavailable, go with the grey model.",
              "Should the Sony be out of stock, Bose is fine.",
              "If you can't find it, get the cheaper one instead.",
              "If they are discontinued, feel free to substitute.",
              "When it is not in stock, switch to the other brand."):
        assert C.search(t), t


def test_condition_without_grant_or_with_ask_instead_is_not_a_grant():
    for t in ("If it is out of stock, just tell me.", "If it's sold out, let me know first.",
              "If it is unavailable, don't substitute it.", "Is it out of stock?", "It might be sold out soon."):
        assert not C.search(t), t


def test_standalone_grants():
    for t in ("A similar one is fine.", "Substitutes are fine.", "Get Sony or the closest thing.",
              "Otherwise the grey one would be fine."):
        assert C.search(t), t


def test_widen_revision_markers():
    for t in ("Actually, make it blue.", "On second thought, I'd rather keep it simple.", "Scratch that.",
              "Change my limit please.", "Let's make it two."):
        assert W.search(t), t


def test_widen_predicates_raise_remove_unrestrict_admit():
    for t in ("Can you raise the limit?", "I can spend more on this.", "We can go higher if needed.",
              "I no longer need the case.", "Drop the charger.", "Any brand works for me.",
              "Color doesn't matter.", "There's no rush.", "Black is fine too.", "Either is fine.",
              "I'm open to other options."):
        assert W.search(t), t


def test_ordinary_pick_or_neutral_turn_is_not_widening():
    for t in ("I'll go with the second one.", "Sounds good, thanks.", "Please keep it under $50.",
              "Ship it to my home address."):
        assert not W.search(t), t
    assert P.search("I'll go with the second one.")
