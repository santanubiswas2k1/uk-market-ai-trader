from __future__ import annotations

from dataclasses import asdict, dataclass

from src.features.context import (
    ENRICHED_FEATURE_COLUMNS,
    build_enriched_feature_frame,
    build_enriched_features,
)
from src.ingest.context_data import load_market_context
from src.ingest.market_data import load_daily_history
from src.ingest.news import load_live_decision_context
from src.markets import get_market, symbol_matches_market
from src.models.ensemble import (
    EnsembleEvaluation,
    ModelMetrics,
    predict_ensemble,
    train_final_ensemble,
    walk_forward_ensemble,
)
from src.models.factory import DEFAULT_MODEL_WEIGHTS
from src.models.persistence import load_model_package, save_model_package


@dataclass(frozen=True)
class Prediction:
    market: str
    market_label: str
    symbol: str
    as_of: str
    close_price: float
    probability_up: float
    probability_down: float
    signal: str
    model_probabilities: dict[str, float]
    model_weights: dict[str, float]
    model_metrics: dict[str, dict[str, float]]
    ensemble_method: str
    model_source: str
    walk_forward_accuracy: float
    walk_forward_brier: float
    walk_forward_folds: int
    labelled_rows: int
    feature_count: int
    decision_context: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _serialise_evaluation(evaluation: EnsembleEvaluation) -> dict:
    return {
        "accuracy": evaluation.accuracy,
        "brier": evaluation.brier,
        "folds": evaluation.folds,
        "model_metrics": {
            name: {
                "accuracy": metrics.accuracy,
                "brier": metrics.brier,
            }
            for name, metrics in evaluation.model_metrics.items()
        },
    }


def _deserialise_evaluation(payload: dict) -> EnsembleEvaluation:
    return EnsembleEvaluation(
        accuracy=float(payload["accuracy"]),
        brier=float(payload["brier"]),
        folds=int(payload["folds"]),
        model_metrics={
            name: ModelMetrics(
                accuracy=float(metrics["accuracy"]),
                brier=float(metrics["brier"]),
            )
            for name, metrics in payload["model_metrics"].items()
        },
    )


def predict_symbol(symbol: str, market: str = "uk", period: str = "5y") -> Prediction:
    """Return a five-model ensemble probability for the selected market."""
    market_config = get_market(market)
    symbol = symbol.upper().strip()

    if not symbol:
        raise ValueError("Symbol is required")
    if not symbol_matches_market(symbol, market):
        raise ValueError(
            f"Symbol {symbol} does not match selected market {market_config.label}"
        )

    stock = load_daily_history(symbol, period=period)
    context = load_market_context(market=market, period=period, symbol=symbol)

    labelled = build_enriched_features(stock, context)
    live_features = build_enriched_feature_frame(stock, context)
    if labelled.empty or live_features.empty:
        raise ValueError(
            f"Not enough aligned price/context data for {symbol} in {market_config.label}"
        )

    latest = live_features.iloc[[-1]]
    training_index = labelled.index[-1]
    training_signature = (
        training_index.isoformat()
        if hasattr(training_index, "isoformat")
        else str(training_index)
    )

    weights = dict(DEFAULT_MODEL_WEIGHTS)
    cache_key = f"{market}/{symbol}"
    package = load_model_package(cache_key)
    model_source = "trained"

    if (
        package
        and package.get("market") == market
        and package.get("training_signature") == training_signature
        and package.get("feature_columns") == ENRICHED_FEATURE_COLUMNS
    ):
        models = package["models"]
        weights = package.get("weights", weights)
        evaluation = _deserialise_evaluation(package["evaluation"])
        model_source = "azure_blob_cache"
    else:
        min_train_rows = min(504, max(252, len(labelled) // 2))
        evaluation = walk_forward_ensemble(
            labelled,
            ENRICHED_FEATURE_COLUMNS,
            min_train_rows=min_train_rows,
            test_rows=40,
            step_rows=40,
            weights=weights,
        )
        models = train_final_ensemble(labelled, ENRICHED_FEATURE_COLUMNS)

        save_model_package(
            cache_key,
            {
                "market": market,
                "training_signature": training_signature,
                "feature_columns": ENRICHED_FEATURE_COLUMNS,
                "weights": weights,
                "evaluation": _serialise_evaluation(evaluation),
                "models": models,
            },
        )

    model_probabilities, probability_up = predict_ensemble(
        models,
        latest,
        ENRICHED_FEATURE_COLUMNS,
        weights=weights,
    )
    probability_down = 1.0 - probability_up

    if probability_up >= 0.60:
        signal = "UP"
    elif probability_up <= 0.40:
        signal = "DOWN"
    else:
        signal = "NEUTRAL"

    last_index = latest.index[-1]
    as_of = last_index.isoformat() if hasattr(last_index, "isoformat") else str(last_index)

    try:
        decision_context = load_live_decision_context(symbol)
    except Exception:  # noqa: BLE001
        decision_context = {
            "sector": None,
            "sector_proxy": None,
            "news_count_24h": 0,
            "news_sentiment": 0.0,
            "recent_headlines": [],
            "next_earnings_date": None,
            "days_to_earnings": None,
            "earnings_within_7d": False,
            "news_used_in_model": False,
            "earnings_used_in_model": False,
        }

    return Prediction(
        market=market,
        market_label=market_config.label,
        symbol=symbol,
        as_of=as_of,
        close_price=float(latest["close"].iloc[0]),
        probability_up=round(probability_up, 4),
        probability_down=round(probability_down, 4),
        signal=signal,
        model_probabilities={
            name: round(value, 4) for name, value in model_probabilities.items()
        },
        model_weights={name: round(value, 4) for name, value in weights.items()},
        model_metrics={
            name: {
                "accuracy": round(metrics.accuracy, 4),
                "brier": round(metrics.brier, 4),
            }
            for name, metrics in evaluation.model_metrics.items()
        },
        ensemble_method="equal_weight",
        model_source=model_source,
        walk_forward_accuracy=round(evaluation.accuracy, 4),
        walk_forward_brier=round(evaluation.brier, 4),
        walk_forward_folds=evaluation.folds,
        labelled_rows=len(labelled),
        feature_count=len(ENRICHED_FEATURE_COLUMNS),
        decision_context=decision_context,
    )
