from factsheet.validate import annualised, check_record, isin_check_digit_ok, peer_flags

TEXT = "ISIN IE00B4L5Y983 TER 0.20% Net Assets of Share Class (M) : 147,192.36 USD Net Assets of Fund (M) : 151,362.25 USD"


def record(**changes):
    base = {"isin": "IE00B4L5Y983", "domicile": "Ireland", "as_of_date": "2026-09-30", "ter_pct": 0.20,
            "fund_aum_m": 151362.25, "top_holdings": []}
    return base | changes


def fields(flags):
    return {field for field, _ in flags}


def test_isin_check_digit():
    assert isin_check_digit_ok("IE00B4L5Y983")
    assert not isin_check_digit_ok("IE00B3VMM847")


def test_clean_record_has_no_flags():
    assert check_record(record(), TEXT) == []


def test_domicile_must_match_isin_prefix():
    assert "domicile" in fields(check_record(record(domicile=None), TEXT))


def test_as_of_date_must_be_month_end():
    assert "as_of_date" in fields(check_record(record(as_of_date="2026-10-05"), TEXT))
    assert "as_of_date" not in fields(check_record(record(as_of_date="2026-08-29"), TEXT))


def test_share_class_assets_are_flagged():
    flags = check_record(record(fund_aum_m=147192.36), TEXT)
    assert ("fund_aum_m", "looks like share class assets") in flags


def test_number_not_in_text_is_flagged():
    assert "fund_aum_m" in fields(check_record(record(fund_aum_m=67761), TEXT))


def test_cumulative_returns_are_annualised():
    assert round(annualised({"fund_5y_pct": 61.05, "multi_year_annualised": False}, "fund_5y_pct"), 1) == 10.0
    assert annualised({"fund_5y_pct": 10.0, "multi_year_annualised": True}, "fund_5y_pct") == 10.0


def test_peer_outlier_is_flagged():
    records = {i: {"fund_1y_pct": v} for i, v in zip("ABCD", [15.2, 15.5, 15.4, -18.3])}
    flags = peer_flags(records, dict.fromkeys("ABCD", "S&P 500"))
    assert flags == [("D", "fund_1y_pct", "-33.6 pts from peer median")]
