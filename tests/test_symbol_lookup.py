from src.services import symbols


class FakeSearch:
    def __init__(self, query: str, max_results: int = 30):
        self.quotes = [
            {
                "symbol": "BARC.L",
                "longname": "Barclays PLC",
                "exchange": "LSE",
                "quoteType": "EQUITY",
            },
            {
                "symbol": "AAPL",
                "longname": "Apple Inc.",
                "exchange": "NMS",
                "quoteType": "EQUITY",
            },
            {
                "symbol": "RELIANCE.NS",
                "longname": "Reliance Industries Limited",
                "exchange": "NSE",
                "quoteType": "EQUITY",
            },
            {
                "symbol": "7203.T",
                "longname": "Toyota Motor Corporation",
                "exchange": "JPX",
                "quoteType": "EQUITY",
            },
            {
                "symbol": "BARC.L",
                "longname": "Barclays PLC duplicate",
                "exchange": "LSE",
                "quoteType": "EQUITY",
            },
        ]


def _search(monkeypatch, query: str, market: str):
    symbols._cached_search.cache_clear()
    monkeypatch.setattr(symbols.yf, "Search", FakeSearch)
    return symbols.search_symbols(query, market=market)


def test_search_symbols_filters_uk(monkeypatch):
    results = _search(monkeypatch, "Barclays", "uk")
    assert [item.symbol for item in results] == ["BARC.L"]


def test_search_symbols_filters_us(monkeypatch):
    results = _search(monkeypatch, "Apple", "us")
    assert [item.symbol for item in results] == ["AAPL"]


def test_search_symbols_filters_india(monkeypatch):
    results = _search(monkeypatch, "Reliance", "india")
    assert [item.symbol for item in results] == ["RELIANCE.NS"]


def test_search_symbols_filters_japan(monkeypatch):
    results = _search(monkeypatch, "Toyota", "japan")
    assert [item.symbol for item in results] == ["7203.T"]
