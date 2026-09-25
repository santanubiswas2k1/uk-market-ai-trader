from src.services.prediction_history import _evaluate_record, _ledger_payload


def _prediction():
    return {
        "market": "us",
        "market_label": "US / NYSE & NASDAQ",
        "symbol": "AAPL",
        "as_of": "2026-09-25T00:00:00+00:00",
        "quote_unit": "USD",
        "close_price": 100.0,
        "probability_up": 0.70,
        "probability_down": 0.30,
        "base_probability_up": 0.65,
        "signal": "UP",
        "expected_return_1d": 0.02,
        "base_expected_return_1d": 0.015,
        "expected_close": 102.0,
        "expected_range_low": 99.0,
        "expected_range_high": 104.0,
        "expected_range_confidence": 0.80,
        "news_sentiment_weight": 0.08,
        "news_probability_up": 0.75,
        "ensemble_method": "equal_weight_plus_news_sentiment_fusion",
        "model_source": "trained",
        "feature_count": 17,
        "decision_context": {
            "news_sentiment": 0.5,
            "news_count_24h": 4,
        },
    }


def test_ledger_payload_is_pending_and_daily_unique():
    payload = _ledger_payload(_prediction())

    assert payload["prediction_id"] == "us/AAPL/2026-09-25"
    assert payload["status"] == "pending"
    assert payload["actual_next_close"] is None
    assert payload["news_sentiment"] == 0.5


def test_evaluate_record_scores_direction_brier_close_return_and_range():
    record = _ledger_payload(_prediction())

    _evaluate_record(
        record,
        actual_as_of="2026-09-28T00:00:00+00:00",
        actual_close=103.0,
    )

    assert record["status"] == "evaluated"
    assert record["actual_direction"] == "UP"
    assert record["direction_correct"] is True
    assert record["signal_correct"] is True
    assert record["range_hit"] is True
    assert record["brier_score"] == 0.09
    assert record["absolute_close_error"] == 1.0
    assert record["actual_return_1d"] == 0.03
    assert record["absolute_return_error"] == 0.01


def test_neutral_signal_is_not_counted_as_signal_accuracy():
    prediction = _prediction()
    prediction["signal"] = "NEUTRAL"
    prediction["probability_up"] = 0.52
    record = _ledger_payload(prediction)

    _evaluate_record(
        record,
        actual_as_of="2026-09-28T00:00:00+00:00",
        actual_close=99.0,
    )

    assert record["direction_correct"] is False
    assert record["signal_correct"] is None
