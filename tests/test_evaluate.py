from factsheet.evaluate import outcome


def test_numbers_within_rounding_are_correct():
    assert outcome("ter_pct", 0.2, 0.20) == "correct"
    assert outcome("fund_1y_pct", 15.25, 15.26) == "correct"
    assert outcome("fund_1y_pct", 15.25, 15.35) == "wrong"


def test_aum_uses_relative_tolerance():
    assert outcome("fund_aum_m", 30970, 30971.5) == "correct"
    assert outcome("fund_aum_m", 152.38, 30970) == "wrong"


def test_null_handling():
    assert outcome("sri", None, None) == "correct"
    assert outcome("sri", None, 4) == "missed"
    assert outcome("sri", 4, None) == "hallucinated"
    assert outcome("top_holdings", [], []) == "correct"


def test_bool_is_not_compared_as_number():
    assert outcome("multi_year_annualised", True, True) == "correct"
    assert outcome("multi_year_annualised", False, True) == "wrong"


def test_text_is_case_insensitive():
    assert outcome("replication", "Physical", "physical") == "correct"
    assert outcome("issuer", "iShares III plc", "iShares") == "wrong"


def test_fund_name_ignores_share_class_suffix():
    assert outcome("fund_name", "UBS Core MSCI World UCITS ETF", "UBS Core MSCI World UCITS ETF USD acc") == "correct"
    assert outcome("fund_name", "UBS MSCI EM SF UCITS ETF 2016", "UBS MSCI EM SF UCITS ETF USD acc") == "wrong"


def test_holdings_match_on_first_word_and_weight():
    truth = [{"name": "NVIDIA Corp.", "weight_pct": 8.4}, {"name": "Apple Inc.", "weight_pct": 7.4}]
    assert outcome("top_holdings", [{"name": "NVIDIA", "weight_pct": 8.4}, {"name": "APPLE", "weight_pct": 7.4}], truth) == "correct"
    assert outcome("top_holdings", [{"name": "NVIDIA", "weight_pct": 8.4}], truth) == "wrong"
