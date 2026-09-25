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



def load_live_quote(symbol: str) -> dict:
    """Load the latest provider quote and intraday snapshot.

    The current Yahoo/yfinance source may be delayed and is not an exchange-
    licensed real-time feed. The response is deliberately labelled accordingly.
    """
    ticker = yf.Ticker(symbol)

    history = ticker.history(
        period="1d",
        interval="1m",
        auto_adjust=False,
        prepost=True,
    )
    if history.empty:
        history = ticker.history(
            period="5d",
            interval="5m",
            auto_adjust=False,
            prepost=True,
        )
    if history.empty:
        raise ValueError(f"No live quote data returned for {symbol}")

    history = history.dropna(subset=["Close"]).copy()
    if history.empty:
        raise ValueError(f"No valid live quote data returned for {symbol}")

    latest = history.iloc[-1]
    first = history.iloc[0]

    try:
        fast_info = ticker.fast_info
    except Exception:  # noqa: BLE001
        fast_info = {}

    def _fast(key: str, default=None):
        try:
            return fast_info.get(key, default)
        except (AttributeError, KeyError, TypeError):
            return default

    price = float(latest["Close"])
    previous_close = _fast("previous_close")
    if previous_close is None:
        previous_close = float(first["Close"])
    else:
        previous_close = float(previous_close)

    change = price - previous_close
    change_percent = change / previous_close if previous_close else 0.0

    day_high = _fast("day_high")
    day_low = _fast("day_low")
    volume = _fast("last_volume")

    if day_high is None and "High" in history:
        day_high = float(history["High"].max())
    if day_low is None and "Low" in history:
        day_low = float(history["Low"].min())
    if volume is None and "Volume" in history:
        volume = int(history["Volume"].fillna(0).sum())

    last_index = history.index[-1]
    last_update = (
        last_index.isoformat()
        if hasattr(last_index, "isoformat")
        else str(last_index)
    )

    return {
        "symbol": symbol.upper(),
        "price": round(price, 4),
        "previous_close": round(previous_close, 4),
        "change": round(change, 4),
        "change_percent": round(change_percent, 6),
        "day_high": round(float(day_high), 4) if day_high is not None else None,
        "day_low": round(float(day_low), 4) if day_low is not None else None,
        "volume": int(volume) if volume is not None else None,
        "currency": _fast("currency"),
        "exchange": _fast("exchange"),
        "last_update": last_update,
        "feed_status": "provider_delayed",
        "feed_source": "Yahoo Finance via yfinance",
    }
