"""Spec MONEY-1 (cdv/m1.py): amounts and upper-bound budget mentions. One test per clause of the spec."""
from cdv import m1

B = m1.budget_mentions


def test_amount_forms_prefix_suffix_codes_separators_decimals_magnitude():
    vals = lambda t: [v for _, _, v in m1.money_amounts(t)]  # noqa: E731
    assert vals("$30") == [30.0] and vals("US$ 40") == [40.0] and vals("USD 1,407") == [1407.0]
    assert vals("€80") == [80.0] and vals("£12.5") == [12.5] and vals("₩5000") == [5000.0]
    assert vals("50 dollars") == [50.0] and vals("2k usd") == [2000.0] and vals("50,000 won") == [50000.0]
    assert vals("19.99 EUR") == [19.99]                                    # a code after the number is a suffix
    assert vals("5만원") == [50000.0] and vals("30000원") == [30000.0]
    assert vals("usd 115") == [115.0]                                      # codes in any case


def test_no_currency_no_budget_word_is_never_money():
    for t in ("within 3 days", "I need 2 of them", "option 1 please", "Ship to 1 Maple Way", "the 10 pcs pack"):
        assert B(t) == [], t


def test_amount_without_bound_is_not_a_budget():
    assert B("it costs $45") == [] and B("the total came to USD 135.58") == []


def test_bound_before_amount_clause_a():
    for t, v in (("under $30", 30), ("less than €80", 80), ("no higher than USD 60", 60), ("up to 50 dollars", 50),
                 ("at most USD 40", 40), ("within USD 1,407", 1407), ("I will not pay more than $70.", 70),
                 ("I can't go over $90", 90), ("keep it under $19.99", 19.99), ("capped at $300", 300),
                 ("spend no more than USD 25", 25)):
        assert B(t) == [v], t


def test_bound_after_amount_clause_b():
    for t, v in (("USD 19.99 max", 19.99), ("$40 or less", 40), ("$1,200 is my limit", 1200),
                 ("with USD 115 as the total limit", 115), ("$75 tops", 75), ("5만원 이하로", 50000)):
        assert B(t) == [v], t


def test_bare_number_needs_budget_word_clause_c():
    assert B("budget is 200") == [200.0] and B("spend up to 150") == [150.0]
    assert B("spend up to 3 days") == []


def test_bound_does_not_cross_clause_boundary():
    assert B("Keep it under control. The lamp is $40.") == []
    assert B("Up to you. It is $25.") == []


def test_multiple_mentions_in_order():
    assert B("First under $50; actually up to $80.") == [50.0, 80.0]
