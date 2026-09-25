from src.services import symbols


class FakeSearch:
    def __init__(self, query: str, max_results: int = 20):
        self.quotes = [
            {
                "symbol": "BARC.L",
                "longname": "Barclays PLC",
                "exchange": "LSE",
                "quoteType": "EQUITY",
            },
            {
                "symbol": "BCS",
                "longname": "Barclays PLC ADR",
                "exchange": "NYQ",
                "quoteType": "EQUITY",
            },
            {
                "symbol": "BARC.L",
                "longname": "Barclays PLC duplicate",
                "exchange": "LSE",
                "quoteType": "EQUITY",
            },
        ]


def test_search_lse_symbols_filters_to_london_equities(monkeypatch):
    symbols._cached_search.cache_clear()
    monkeypatch.setattr(symbols.yf, "Search", FakeSearch)

    results = symbols.search_lse_symbols("Barclays")

    assert len(results) == 1
    assert results[0].symbol == "BARC.L"
    assert results[0].name == "Barclays PLC"
