from __future__ import annotations

from dataclasses import asdict, dataclass

from src.features.context import (
    ENRICHED_FEATURE_COLUMNS,
    build_enriched_feature_frame,
    build_enriched_features,
)
from src.ingest.context_data import load_market_context
from src.ingest.market_data import load_daily_history
from src.models.train import train_final
from src.models.walkforward import walk_forward_evaluate


@dataclass(frozen=True)
class Prediction:
    symbol: str
    as_of: str
    close_price: float
    probability_up: float
    probability_down: float
    signal: str
    walk_forward_accuracy: float
    walk_forward_brier: float
    walk_forward_folds: int
    labelled_rows: int
    feature_count: int

    def to_dict(self) -> dict:
        return asdict(self)


def predict_symbol(symbol: str, period: str = "5y") -> Prediction:
    """Train and score a next-trading-day UK equity research model."""
    symbol = symbol.upper().strip()
    if not symbol.endswith(".L"):
        raise ValueError("Use a London Stock Exchange symbol ending in .L, e.g. BARC.L")

    stock = load_daily_history(symbol, period=period)
    context = load_market_context(period=period)

    labelled = build_enriched_features(stock, context)
    live_features = build_enriched_feature_frame(stock, context)

    min_train_rows = min(504, max(252, len(labelled) // 2))
    evaluation = walk_forward_evaluate(
        labelled,
        ENRICHED_FEATURE_COLUMNS,
        min_train_rows=min_train_rows,
        test_rows=20,
        step_rows=20,
    )
    final_model = train_final(labelled, ENRICHED_FEATURE_COLUMNS)

    latest = live_features.iloc[[-1]]
    probability_up = float(
        final_model.predict_proba(latest[ENRICHED_FEATURE_COLUMNS])[:, 1][0]
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

    return Prediction(
        symbol=symbol,
        as_of=as_of,
        close_price=float(latest["close"].iloc[0]),
        probability_up=round(probability_up, 4),
        probability_down=round(probability_down, 4),
        signal=signal,
        walk_forward_accuracy=round(evaluation.accuracy, 4),
        walk_forward_brier=round(evaluation.brier, 4),
        walk_forward_folds=evaluation.folds,
        labelled_rows=len(labelled),
        feature_count=len(ENRICHED_FEATURE_COLUMNS),
    )
