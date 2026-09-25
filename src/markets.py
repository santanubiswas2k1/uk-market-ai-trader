from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketConfig:
    key: str
    label: str
    index_tickers: tuple[str, ...]
    fx_tickers: tuple[str, ...]
    symbol_suffixes: tuple[str, ...]
    exchange_names: tuple[str, ...]
    default_symbol: str


MARKETS: dict[str, MarketConfig] = {
    "uk": MarketConfig(
        key="uk",
        label="UK / LSE",
        index_tickers=("^FTSE",),
        fx_tickers=("GBPUSD=X",),
        symbol_suffixes=(".L",),
        exchange_names=("LSE", "London Stock Exchange"),
        default_symbol="BARC.L",
    ),
    "us": MarketConfig(
        key="us",
        label="US / NYSE & NASDAQ",
        index_tickers=("^GSPC", "^IXIC"),
        fx_tickers=("DX-Y.NYB",),
        symbol_suffixes=(),
        exchange_names=("NMS", "NYQ", "NAS", "NYSE", "NASDAQ", "NasdaqGS", "NasdaqCM"),
        default_symbol="AAPL",
    ),
    "india": MarketConfig(
        key="india",
        label="India / NSE & BSE",
        index_tickers=("^NSEI", "^BSESN"),
        fx_tickers=("INR=X",),
        symbol_suffixes=(".NS", ".BO"),
        exchange_names=("NSE", "BSE"),
        default_symbol="RELIANCE.NS",
    ),
    "uae": MarketConfig(
        key="uae",
        label="UAE / DFM & ADX",
        index_tickers=("^DFMGI", "^ADI", "UAE"),
        fx_tickers=("AED=X",),
        symbol_suffixes=(".DU", ".AE"),
        exchange_names=("DFM", "ADX", "Abu Dhabi", "Dubai"),
        default_symbol="EMAAR.DU",
    ),
    "canada": MarketConfig(
        key="canada",
        label="Canada / TSX",
        index_tickers=("^GSPTSE",),
        fx_tickers=("CAD=X",),
        symbol_suffixes=(".TO", ".V"),
        exchange_names=("TOR", "TSX", "TSXV", "Toronto"),
        default_symbol="RY.TO",
    ),
    "europe": MarketConfig(
        key="europe",
        label="Europe / Major Exchanges",
        index_tickers=("^STOXX50E", "^STOXX"),
        fx_tickers=("EURUSD=X",),
        symbol_suffixes=(".DE", ".PA", ".AS", ".MI", ".MC", ".BR", ".LS", ".VI"),
        exchange_names=("GER", "PAR", "AMS", "MIL", "MCE", "BRU", "LIS", "VIE"),
        default_symbol="SAP.DE",
    ),
    "hong_kong": MarketConfig(
        key="hong_kong",
        label="Hong Kong / HKEX",
        index_tickers=("^HSI",),
        fx_tickers=("HKD=X",),
        symbol_suffixes=(".HK",),
        exchange_names=("HKG", "HKSE", "Hong Kong"),
        default_symbol="0700.HK",
    ),
    "japan": MarketConfig(
        key="japan",
        label="Japan / TSE",
        index_tickers=("^N225",),
        fx_tickers=("JPY=X",),
        symbol_suffixes=(".T",),
        exchange_names=("JPX", "TYO", "Tokyo"),
        default_symbol="7203.T",
    ),
    "australia": MarketConfig(
        key="australia",
        label="Australia / ASX",
        index_tickers=("^AXJO",),
        fx_tickers=("AUDUSD=X",),
        symbol_suffixes=(".AX",),
        exchange_names=("ASX", "Australian"),
        default_symbol="BHP.AX",
    ),
}


def get_market(market: str) -> MarketConfig:
    key = market.strip().lower()
    try:
        return MARKETS[key]
    except KeyError as exc:
        supported = ", ".join(MARKETS)
        raise ValueError(f"Unsupported market '{market}'. Supported markets: {supported}") from exc


def symbol_matches_market(symbol: str, market: str) -> bool:
    config = get_market(market)
    normalized = symbol.upper().strip()

    if market.strip().lower() == "us":
        return bool(normalized)

    if config.symbol_suffixes:
        return normalized.endswith(config.symbol_suffixes)

    return bool(normalized)
