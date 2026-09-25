from src.markets import MARKETS, get_market, symbol_matches_market


def test_expected_markets_are_configured():
    assert set(MARKETS) == {
        "uk",
        "us",
        "india",
        "uae",
        "canada",
        "europe",
        "hong_kong",
        "japan",
        "australia",
    }


def test_market_symbol_validation():
    assert symbol_matches_market("BARC.L", "uk")
    assert symbol_matches_market("AAPL", "us")
    assert symbol_matches_market("RELIANCE.NS", "india")
    assert symbol_matches_market("RY.TO", "canada")
    assert symbol_matches_market("SAP.DE", "europe")
    assert symbol_matches_market("0700.HK", "hong_kong")
    assert symbol_matches_market("7203.T", "japan")
    assert symbol_matches_market("BHP.AX", "australia")


def test_market_has_context_and_default_symbol():
    for key in MARKETS:
        market = get_market(key)
        assert market.index_tickers
        assert market.fx_tickers
        assert market.default_symbol
