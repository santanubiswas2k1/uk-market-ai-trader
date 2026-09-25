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
    except Exception:
        return None

    sector = info.get("sector")
    return str(sector).strip() if sector else None


def sector_proxy_ticker(symbol: str) -> str | None:
    sector = get_symbol_sector(symbol)
    if not sector:
        return None
    return SECTOR_ETFS.get(sector.casefold())
