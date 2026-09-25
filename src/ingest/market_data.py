from __future__ import annotations

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
