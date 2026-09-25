from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
import yfinance as yf

from src.ingest.market_data import get_symbol_sector, sector_proxy_ticker

POSITIVE_WORDS = {
    "beat", "beats", "growth", "upgrade", "upgraded", "raises", "raised",
    "record", "strong", "surge", "surges", "profit", "profits", "wins", "win",
    "approval", "approved", "bullish", "outperform", "buy", "expands",
}
NEGATIVE_WORDS = {
    "miss", "misses", "downgrade", "downgraded", "cuts", "cut", "warning",
    "weak", "falls", "fall", "loss", "losses", "lawsuit", "probe", "investigation",
    "recall", "bearish", "underperform", "sell", "fraud", "decline",
}


def _headline(item: dict[str, Any]) -> str:
    content = item.get("content")
    if isinstance(content, dict):
        title = content.get("title")
        if title:
            return str(title)
    return str(item.get("title") or "").strip()


def _published_at(item: dict[str, Any]) -> datetime | None:
    raw = item.get("providerPublishTime")
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw, tz=UTC)

    content = item.get("content")
    if isinstance(content, dict):
        raw = content.get("pubDate")
    if raw:
        try:
            stamp = pd.to_datetime(raw, utc=True)
            return stamp.to_pydatetime()
        except Exception:  # noqa: BLE001
            return None
    return None


def _sentiment_score(title: str) -> int:
    words = {
        token.strip(".,:;!?()[]{}'\"").casefold()
        for token in title.split()
    }
    positive = len(words & POSITIVE_WORDS)
    negative = len(words & NEGATIVE_WORDS)
    return positive - negative


def _next_earnings_date(ticker: yf.Ticker) -> datetime | None:
    try:
        calendar = ticker.calendar
    except Exception:  # noqa: BLE001
        return None

    values: list[Any] = []
    if isinstance(calendar, dict):
        raw = calendar.get("Earnings Date")
        values = raw if isinstance(raw, list) else [raw]
    elif isinstance(calendar, pd.DataFrame) and "Earnings Date" in calendar.index:
        raw = calendar.loc["Earnings Date"]
        values = list(raw) if hasattr(raw, "__iter__") and not isinstance(raw, str) else [raw]

    now = datetime.now(UTC)
    dates: list[datetime] = []
    for value in values:
        if value is None:
            continue
        try:
            parsed = pd.to_datetime(value, utc=True).to_pydatetime()
            if parsed >= now:
                dates.append(parsed)
        except Exception:  # noqa: BLE001, S112
            continue
    return min(dates) if dates else None


def load_live_decision_context(symbol: str) -> dict[str, Any]:
    """Return current news/earnings context. These fields are not historical model inputs."""
    ticker = yf.Ticker(symbol)
    try:
        raw_news = ticker.news or []
    except Exception:  # noqa: BLE001
        raw_news = []

    now = datetime.now(UTC)
    scored: list[tuple[str, int, datetime | None]] = []
    for item in raw_news[:20]:
        if not isinstance(item, dict):
            continue
        title = _headline(item)
        if not title:
            continue
        scored.append((title, _sentiment_score(title), _published_at(item)))

    last_24h = [
        row for row in scored
        if row[2] is not None and 0 <= (now - row[2]).total_seconds() <= 86400
    ]
    sentiment_sum = sum(score for _, score, _ in last_24h)
    sentiment = 0.0
    if last_24h:
        sentiment = max(-1.0, min(1.0, sentiment_sum / max(1, len(last_24h))))

    earnings = _next_earnings_date(ticker)
    days_to_earnings = None
    if earnings is not None:
        days_to_earnings = max(0, (earnings.date() - now.date()).days)

    return {
        "sector": get_symbol_sector(symbol),
        "sector_proxy": sector_proxy_ticker(symbol),
        "news_count_24h": len(last_24h),
        "news_sentiment": round(sentiment, 3),
        "recent_headlines": [title for title, _, _ in scored[:5]],
        "next_earnings_date": earnings.isoformat() if earnings else None,
        "days_to_earnings": days_to_earnings,
        "earnings_within_7d": days_to_earnings is not None and days_to_earnings <= 7,
        "news_used_in_model": False,
        "earnings_used_in_model": False,
    }


NEWS_MAX_WEIGHT = 0.12


def fuse_news_sentiment(
    base_probability_up: float,
    base_expected_return: float,
    daily_vol: float,
    context: dict[str, Any],
) -> dict[str, float | bool]:
    """Blend current news sentiment into the live forecast with a bounded weight.

    This live overlay is intentionally separate from historical walk-forward metrics
    until point-in-time historical news data is available for proper backtesting.
    """
    count = max(0, int(context.get("news_count_24h") or 0))
    sentiment = float(context.get("news_sentiment") or 0.0)
    sentiment = max(-1.0, min(1.0, sentiment))

    coverage = min(count / 5.0, 1.0)
    news_weight = NEWS_MAX_WEIGHT * coverage
    news_probability_up = 0.5 + 0.5 * sentiment

    adjusted_probability_up = (
        (1.0 - news_weight) * base_probability_up
        + news_weight * news_probability_up
    )
    adjusted_probability_up = max(0.01, min(0.99, adjusted_probability_up))

    return_tilt = news_weight * sentiment * max(0.0, daily_vol)
    adjusted_expected_return = base_expected_return + return_tilt

    days_to_earnings = context.get("days_to_earnings")
    earnings_range_multiplier = 1.0
    if isinstance(days_to_earnings, int):
        if days_to_earnings <= 1:
            earnings_range_multiplier = 1.50
        elif days_to_earnings <= 3:
            earnings_range_multiplier = 1.35
        elif days_to_earnings <= 7:
            earnings_range_multiplier = 1.20

    return {
        "news_used_in_algorithm": news_weight > 0.0,
        "news_weight": news_weight,
        "news_probability_up": news_probability_up,
        "adjusted_probability_up": adjusted_probability_up,
        "return_tilt": return_tilt,
        "adjusted_expected_return": adjusted_expected_return,
        "earnings_range_multiplier": earnings_range_multiplier,
        "news_overlay_backtested": False,
    }
