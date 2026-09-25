from __future__ import annotations

import pandas as pd
import yfinance as yf

from src.markets import get_market


def _download_close(symbol: str, period: str) -> pd.Series:
    df = yf.download(symbol, period=period, auto_adjust=False, progress=False)
    if df.empty:
        raise ValueError(f"No context data returned for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    close = df["Close"].copy()
    close.index = pd.to_datetime(close.index, utc=True)
    return close.astype(float)


def _download_first_available(candidates: tuple[str, ...], period: str) -> pd.Series:
    errors: list[str] = []
    for symbol in candidates:
        try:
            return _download_close(symbol, period)
        except Exception as exc:
            errors.append(f"{symbol}: {exc}")

    joined = "; ".join(errors)
    raise ValueError(f"No context data available from configured tickers. {joined}")


def load_market_context(market: str = "uk", period: str = "5y") -> pd.DataFrame:
    """Load daily market-index and FX context for the selected market."""
    config = get_market(market)

    out = pd.DataFrame()
    out["market_close"] = _download_first_available(config.index_tickers, period)
    out["fx_close"] = _download_first_available(config.fx_tickers, period)

    return out.sort_index().ffill()
