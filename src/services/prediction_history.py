from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from azure.core.exceptions import AzureError, ResourceExistsError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from src.ingest.market_data import load_daily_history

CONTAINER_NAME = "predictions"


def _service_client() -> BlobServiceClient | None:
    account_url = os.getenv("MODEL_STORAGE_ACCOUNT_URL", "").strip()
    if not account_url:
        return None

    return BlobServiceClient(
        account_url=account_url,
        credential=DefaultAzureCredential(),
    )


def _container():
    service = _service_client()
    if service is None:
        return None

    container = service.get_container_client(CONTAINER_NAME)
    try:
        container.create_container()
    except ResourceExistsError:
        pass
    except AzureError:
        return None
    return container


def _forecast_date(as_of: str) -> str:
    return pd.to_datetime(as_of, utc=True).date().isoformat()


def _blob_name(payload: dict[str, Any]) -> str:
    market = str(payload["market"]).lower()
    symbol = str(payload["symbol"]).upper()
    forecast_date = _forecast_date(str(payload["as_of"]))
    return f"{market}/{symbol}/{forecast_date}.json"


def _ledger_payload(prediction: dict[str, Any]) -> dict[str, Any]:
    context = prediction.get("decision_context") or {}
    return {
        "prediction_id": _blob_name(prediction).removesuffix(".json"),
        "created_at": datetime.now(UTC).isoformat(),
        "status": "pending",
        "market": prediction["market"],
        "market_label": prediction.get("market_label"),
        "symbol": prediction["symbol"],
        "as_of": prediction["as_of"],
        "quote_unit": prediction.get("quote_unit"),
        "close_price": prediction["close_price"],
        "probability_up": prediction["probability_up"],
        "probability_down": prediction["probability_down"],
        "base_probability_up": prediction.get("base_probability_up"),
        "signal": prediction["signal"],
        "expected_return_1d": prediction["expected_return_1d"],
        "base_expected_return_1d": prediction.get("base_expected_return_1d"),
        "expected_close": prediction["expected_close"],
        "expected_range_low": prediction["expected_range_low"],
        "expected_range_high": prediction["expected_range_high"],
        "expected_range_confidence": prediction.get("expected_range_confidence"),
        "news_sentiment": context.get("news_sentiment"),
        "news_count_24h": context.get("news_count_24h"),
        "news_sentiment_weight": prediction.get("news_sentiment_weight"),
        "news_probability_up": prediction.get("news_probability_up"),
        "ensemble_method": prediction.get("ensemble_method"),
        "model_source": prediction.get("model_source"),
        "feature_count": prediction.get("feature_count"),
        "actual_next_close": None,
        "actual_return_1d": None,
        "actual_direction": None,
        "direction_correct": None,
        "signal_correct": None,
        "brier_score": None,
        "absolute_close_error": None,
        "absolute_close_error_pct": None,
        "absolute_return_error": None,
        "range_hit": None,
        "actual_as_of": None,
        "evaluated_at": None,
    }


def record_prediction(prediction: dict[str, Any]) -> dict[str, Any]:
    """Persist the first forecast for market/symbol/as-of date."""
    container = _container()
    if container is None:
        return {
            "recorded": False,
            "created": False,
            "prediction_id": None,
            "reason": "storage_unavailable",
        }

    payload = _ledger_payload(prediction)
    name = _blob_name(prediction)
    blob = container.get_blob_client(name)

    try:
        blob.upload_blob(
            json.dumps(payload, separators=(",", ":")),
            overwrite=False,
            content_type="application/json",
        )
        return {
            "recorded": True,
            "created": True,
            "prediction_id": payload["prediction_id"],
        }
    except ResourceExistsError:
        return {
            "recorded": True,
            "created": False,
            "prediction_id": payload["prediction_id"],
        }
    except AzureError:
        return {
            "recorded": False,
            "created": False,
            "prediction_id": payload["prediction_id"],
            "reason": "storage_error",
        }


def _load_record(container, name: str) -> dict[str, Any] | None:
    try:
        raw = container.download_blob(name).readall()
        record = json.loads(raw)
        record["_blob_name"] = name
        return record
    except (AzureError, ResourceNotFoundError, json.JSONDecodeError):
        return None


def _save_record(container, record: dict[str, Any]) -> None:
    name = record["_blob_name"]
    payload = {key: value for key, value in record.items() if key != "_blob_name"}
    container.upload_blob(
        name=name,
        data=json.dumps(payload, separators=(",", ":")),
        overwrite=True,
        content_type="application/json",
    )


def list_prediction_records(
    market: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    container = _container()
    if container is None:
        return []

    prefix = f"{market.lower()}/" if market else None
    records: list[dict[str, Any]] = []
    try:
        blobs = container.list_blobs(name_starts_with=prefix)
        names = sorted(
            (blob.name for blob in blobs if blob.name.endswith(".json")),
            reverse=True,
        )
    except AzureError:
        return []

    for name in names[:limit]:
        record = _load_record(container, name)
        if record is not None:
            records.append(record)
    return records


def _next_completed_close(
    symbol: str,
    as_of: str,
) -> tuple[str, float] | None:
    history = load_daily_history(symbol, period="1y")
    forecast_time = pd.to_datetime(as_of, utc=True)
    future = history.loc[history.index > forecast_time]
    if future.empty:
        return None

    next_index = future.index[0]
    if next_index.date() >= datetime.now(UTC).date():
        return None

    return next_index.isoformat(), float(future.iloc[0]["close"])


def _evaluate_record(record: dict[str, Any], actual_as_of: str, actual_close: float) -> None:
    forecast_close = float(record["close_price"])
    probability_up = float(record["probability_up"])
    expected_return = float(record["expected_return_1d"])
    expected_close = float(record["expected_close"])
    range_low = float(record["expected_range_low"])
    range_high = float(record["expected_range_high"])

    actual_return = actual_close / forecast_close - 1.0
    actual_up = actual_return > 0.0
    predicted_up = probability_up >= 0.5

    signal = str(record.get("signal") or "NEUTRAL").upper()
    signal_correct: bool | None
    if signal == "UP":
        signal_correct = actual_up
    elif signal == "DOWN":
        signal_correct = not actual_up
    else:
        signal_correct = None

    record.update(
        {
            "status": "evaluated",
            "actual_next_close": round(actual_close, 6),
            "actual_return_1d": round(actual_return, 8),
            "actual_direction": "UP" if actual_up else "DOWN",
            "direction_correct": predicted_up == actual_up,
            "signal_correct": signal_correct,
            "brier_score": round((probability_up - float(actual_up)) ** 2, 8),
            "absolute_close_error": round(abs(expected_close - actual_close), 6),
            "absolute_close_error_pct": round(
                abs(expected_close - actual_close) / actual_close,
                8,
            ),
            "absolute_return_error": round(
                abs(expected_return - actual_return),
                8,
            ),
            "range_hit": range_low <= actual_close <= range_high,
            "actual_as_of": actual_as_of,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }
    )


def reconcile_predictions(
    market: str | None = None,
    limit: int = 250,
) -> int:
    container = _container()
    if container is None:
        return 0

    records = list_prediction_records(market=market, limit=limit)
    pending = [record for record in records if record.get("status") != "evaluated"]
    completed = 0
    cache: dict[tuple[str, str], tuple[str, float] | None] = {}

    for record in pending:
        key = (str(record["symbol"]), str(record["as_of"]))
        if key not in cache:
            try:
                cache[key] = _next_completed_close(*key)
            except (ValueError, KeyError):
                cache[key] = None

        actual = cache[key]
        if actual is None:
            continue

        actual_as_of, actual_close = actual
        _evaluate_record(record, actual_as_of, actual_close)
        try:
            _save_record(container, record)
            completed += 1
        except AzureError:
            continue

    return completed


def performance_summary(
    market: str | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    reconciled = reconcile_predictions(market=market, limit=limit)
    records = list_prediction_records(market=market, limit=limit)
    evaluated = [record for record in records if record.get("status") == "evaluated"]
    pending = [record for record in records if record.get("status") != "evaluated"]

    if not evaluated:
        return {
            "market": market,
            "total_predictions": len(records),
            "evaluated_predictions": 0,
            "pending_predictions": len(pending),
            "reconciled_now": reconciled,
            "direction_accuracy": None,
            "signal_accuracy": None,
            "brier_score": None,
            "expected_close_mae": None,
            "expected_close_mape": None,
            "return_mae": None,
            "range_hit_rate": None,
            "recent": [],
        }

    signal_records = [
        record for record in evaluated if record.get("signal_correct") is not None
    ]

    def avg(field: str, rows: list[dict[str, Any]] = evaluated) -> float:
        return sum(float(row[field]) for row in rows) / len(rows)

    recent = [
        {
            key: record.get(key)
            for key in (
                "prediction_id",
                "market",
                "symbol",
                "as_of",
                "signal",
                "probability_up",
                "expected_close",
                "actual_next_close",
                "actual_return_1d",
                "direction_correct",
                "signal_correct",
                "range_hit",
                "evaluated_at",
            )
        }
        for record in evaluated[:20]
    ]

    return {
        "market": market,
        "total_predictions": len(records),
        "evaluated_predictions": len(evaluated),
        "pending_predictions": len(pending),
        "reconciled_now": reconciled,
        "direction_accuracy": avg("direction_correct"),
        "signal_accuracy": (
            avg("signal_correct", signal_records) if signal_records else None
        ),
        "brier_score": avg("brier_score"),
        "expected_close_mae": avg("absolute_close_error"),
        "expected_close_mape": avg("absolute_close_error_pct"),
        "return_mae": avg("absolute_return_error"),
        "range_hit_rate": avg("range_hit"),
        "recent": recent,
    }
