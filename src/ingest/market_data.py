from __future__ import annotations

from functools import lru_cache
import logging

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

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



def _extract_universe_frames(
    frame: pd.DataFrame,
    symbols: list[str],
) -> dict[str, pd.DataFrame]:
    if frame.empty:
        return {}

    results: dict[str, pd.DataFrame] = {}
    if not isinstance(frame.columns, pd.MultiIndex):
        if len(symbols) != 1:
            return {}
        single = frame.copy().rename(columns=str.lower).dropna(how="all")
        if single.empty:
            return {}
        single.index = pd.to_datetime(single.index, utc=True)
        single["symbol"] = symbols[0]
        return {symbols[0]: single}

    symbol_set = set(symbols)
    level_scores = []
    for level in range(frame.columns.nlevels):
        values = {str(value) for value in frame.columns.get_level_values(level)}
        level_scores.append(len(values & symbol_set))

    ticker_level = max(range(len(level_scores)), key=level_scores.__getitem__)
    if level_scores[ticker_level] == 0:
        if len(symbols) != 1:
            return {}
        ticker_level = frame.columns.nlevels - 1

    available = {
        str(value) for value in frame.columns.get_level_values(ticker_level)
    }
    for symbol in symbols:
        if symbol not in available:
            continue

        try:
            single = frame.xs(symbol, axis=1, level=ticker_level).copy()
        except KeyError:
            continue

        if isinstance(single.columns, pd.MultiIndex):
            single.columns = [str(column[0]) for column in single.columns]
        single = single.rename(columns=str.lower).dropna(how="all")
        if single.empty or "close" not in single.columns:
            continue

        single.index = pd.to_datetime(single.index, utc=True)
        single["symbol"] = symbol
        results[symbol] = single

    return results


def _download_universe_batch(
    symbols: list[str],
    period: str,
    *,
    threads: bool,
) -> dict[str, pd.DataFrame]:
    if not symbols:
        return {}

    try:
        frame = yf.download(
            symbols,
            period=period,
            auto_adjust=False,
            progress=False,
            group_by="ticker",
            threads=threads,
        )
    except Exception:  # noqa: BLE001
        return {}

    return _extract_universe_frames(frame, symbols)


def load_universe_history(
    symbols: tuple[str, ...] | list[str],
    period: str = "6mo",
) -> dict[str, pd.DataFrame]:
    """Load scanner history with a fast batch request and targeted fallbacks."""
    normalized = [symbol.upper().strip() for symbol in symbols if symbol.strip()]
    if not normalized:
        return {}

    results = _download_universe_batch(normalized, period, threads=True)
    missing = [symbol for symbol in normalized if symbol not in results]

    for offset in range(0, len(missing), 3):
        chunk = missing[offset : offset + 3]
        recovered = _download_universe_batch(chunk, period, threads=False)
        results.update(recovered)

    missing = [symbol for symbol in normalized if symbol not in results]
    for symbol in missing:
        try:
            results[symbol] = load_daily_history(symbol, period=period)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Scanner history fallback failed for %s: %s",
                symbol,
                exc,
            )

    return results
