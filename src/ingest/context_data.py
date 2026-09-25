from __future__ import annotations

from functools import lru_cache

import pandas as pd
import yfinance as yf

from src.ingest.market_data import sector_proxy_ticker
from src.markets import get_market

RISK_TICKERS = {
    "vix": "^VIX",
    "us10y": "^TNX",
    "oil": "CL=F",
    "gold": "GC=F",
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


def _download_first_available(candidates: tuple[str, ...], period: str) -> pd.Series:
    errors: list[str] = []
    for symbol in candidates:
        try:
            return _download_close(symbol, period)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{symbol}: {exc}")

    joined = "; ".join(errors)
    raise ValueError(f"No context data available from configured tickers. {joined}")


def _optional_close(symbol: str, period: str, fallback: pd.Series) -> pd.Series:
    try:
        return _download_close(symbol, period)
    except Exception:  # noqa: BLE001
        return fallback.copy()


@lru_cache(maxsize=128)
def load_market_context(
    market: str = "uk",
    period: str = "5y",
    symbol: str | None = None,
) -> pd.DataFrame:
    """Load market, FX, sector and global risk context for daily modelling."""
    config = get_market(market)

    out = pd.DataFrame()
    out["market_close"] = _download_first_available(config.index_tickers, period)
    out["fx_close"] = _download_first_available(config.fx_tickers, period)

    sector_ticker = sector_proxy_ticker(symbol) if symbol else None
    out["sector_close"] = (
        _optional_close(sector_ticker, period, out["market_close"])
        if sector_ticker
        else out["market_close"].copy()
    )

    for name, ticker in RISK_TICKERS.items():
        out[f"{name}_close"] = _optional_close(ticker, period, out["market_close"])

    return out.sort_index().ffill()
