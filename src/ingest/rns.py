from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {"timestamp", "symbol"}


def aggregate_rns_daily(events: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Normalize vendor-supplied RNS events into daily model features.

    Expected columns:
      timestamp, symbol
    Optional columns:
      sentiment_score, importance

    This module intentionally does not scrape RNS. Production ingestion should
    use an appropriately licensed feed/API and pass normalized events here.
    """
    missing = REQUIRED_COLUMNS - set(events.columns)
    if missing:
        raise ValueError(f"RNS events missing columns: {sorted(missing)}")

    df = events.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["symbol"] = df["symbol"].astype(str).str.upper()
    df = df[df["symbol"] == symbol.upper()].copy()

    if "sentiment_score" not in df.columns:
        df["sentiment_score"] = 0.0
    if "importance" not in df.columns:
        df["importance"] = 1.0

    df["date"] = df["timestamp"].dt.normalize()
    grouped = df.groupby("date").agg(
        rns_event_count=("symbol", "size"),
        rns_sentiment_sum=("sentiment_score", "sum"),
        rns_importance_sum=("importance", "sum"),
    )
    return grouped.sort_index()
