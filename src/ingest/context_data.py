from __future__ import annotations

import pandas as pd
import yfinance as yf


CONTEXT_TICKERS = {
    "ftse": "^FTSE",
    "gbpusd": "GBPUSD=X",
}


def _download_close(symbol: str, period: str) -> pd.Series:
    df = yf.download(symbol, period=period, auto_adjust=False, progress=False)
    if df.empty:
        raise ValueError(f"No context data returned for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    close = df["Close"].copy()
    close.index = pd.to_datetime(close.index, utc=True)
    return close.astype(float)


def load_market_context(period: str = "5y") -> pd.DataFrame:
    """Load FTSE 100 and GBP/USD daily context for research use."""
    out = pd.DataFrame()
    for name, ticker in CONTEXT_TICKERS.items():
        out[f"{name}_close"] = _download_close(ticker, period)
    return out.sort_index().ffill()
