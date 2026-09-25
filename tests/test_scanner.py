import pandas as pd

from src.services.scanner import _score_candidate, _technical_snapshot


def _frame() -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=30, freq="B", tz="UTC")
    close = [100 + i * 0.2 for i in range(30)]
    volume = [1_000_000 for _ in range(29)] + [2_200_000]
    return pd.DataFrame({"close": close, "volume": volume}, index=index)


def test_technical_snapshot_detects_unusual_volume_and_momentum():
    snapshot = _technical_snapshot(_frame())

    assert snapshot["last_close"] > 100
    assert snapshot["return_5d"] > 0
    assert snapshot["volume_ratio_20d"] > 2.0
    assert 0.0 <= snapshot["range_position_20d"] <= 1.0
    assert 0.0 <= snapshot["breakout_score"] <= 1.0


def test_score_candidate_is_explainable_and_non_directional():
    technical = {
        "last_close": 105.0,
        "return_1d": 0.03,
        "return_5d": 0.06,
        "volume_ratio_20d": 2.0,
        "volatility_ratio": 1.6,
        "breakout_score": 0.8,
        "range_position_20d": 0.95,
    }
    context = {
        "news_count_24h": 3,
        "news_sentiment": 0.7,
        "earnings_within_7d": True,
    }

    candidate = _score_candidate(
        symbol="AAPL",
        market="us",
        technical=technical,
        context=context,
    )

    assert candidate.score >= 60
    assert candidate.activity in {"High", "Very High"}
    assert "unusual volume" in candidate.reasons
    assert "volatility expanding" in candidate.reasons
    assert "earnings within 7 days" in candidate.reasons
