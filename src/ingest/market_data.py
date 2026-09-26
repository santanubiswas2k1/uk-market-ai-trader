from __future__ import annotations

from functools import lru_cache

import pandas as pd
import yfinance as yf

DEFAULT_UNIVERSE = [
    "AZN.L",
    "SHEL.L",
    "HSBA.L",
    "BARC.L",
    "LLOY.L",
    "BP.L",
    "GSK.L",
    "RR.L",
    "ULVR.L",
    "NG.L",
]

SECTOR_ETFS = {
    "technology": "XLK",
    "financial services": "XLF",
    "financial": "XLF",
    "healthcare": "XLV",
    "energy": "XLE",
    "consumer cyclical": "XLY",
    "consumer defensive": "XLP",
    "industrials": "XLI",
    "basic materials": "XLB",
    "real estate": "XLRE",
    "utilities": "XLU",
    "communication services": "XLC",
}


def load_daily_history(symbol: str, period: str = "5y") -> pd.DataFrame:
    """Load daily research data.

    yfinance is used only as a low-friction MVP source. Replace it with a licensed
    production market-data feed before any live or commercial use.
    """
    df = yf.download(symbol, period=period, auto_adjust=False, progress=False)
    if df.empty:
        raise ValueError(f"No data returned for {symbol}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    df = df.rename(columns=str.lower)
    df.index = pd.to_datetime(df.index, utc=True)
    df["symbol"] = symbol
    return df


@lru_cache(maxsize=256)
def get_symbol_sector(symbol: str) -> str | None:
    """Return the provider-reported sector when available."""
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception:  # noqa: BLE001
        return None

    sector = info.get("sector")
    return str(sector).strip() if sector else None


def sector_proxy_ticker(symbol: str) -> str | None:
    sector = get_symbol_sector(symbol)
    if not sector:
        return None
    return SECTOR_ETFS.get(sector.casefold())



def load_universe_history(
    symbols: tuple[str, ...] | list[str],
    period: str = "6mo",
) -> dict[str, pd.DataFrame]:
    """Load multiple symbols in one Yahoo request for lightweight market scans."""
    normalized = [symbol.upper().strip() for symbol in symbols if symbol.strip()]
    if not normalized:
        return {}

    df = yf.download(
        normalized,
        period=period,
        auto_adjust=False,
        progress=False,
        group_by="ticker",
        threads=True,
    )
    if df.empty:
        return {}

    results: dict[str, pd.DataFrame] = {}
    if len(normalized) == 1:
        single = df.copy()
        if isinstance(single.columns, pd.MultiIndex):
            single.columns = [column[-1] for column in single.columns]
        single = single.rename(columns=str.lower).dropna(how="all")
        if not single.empty:
            single.index = pd.to_datetime(single.index, utc=True)
            single["symbol"] = normalized[0]
            results[normalized[0]] = single
        return results

    if not isinstance(df.columns, pd.MultiIndex):
        return {}

    level_zero = {str(value) for value in df.columns.get_level_values(0)}
    for symbol in normalized:
        if symbol not in level_zero:
            continue
        single = df[symbol].copy().rename(columns=str.lower).dropna(how="all")
        if single.empty:
            continue
        single.index = pd.to_datetime(single.index, utc=True)
        single["symbol"] = symbol
        results[symbol] = single

    return results
