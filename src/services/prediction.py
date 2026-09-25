from __future__ import annotations

from dataclasses import asdict, dataclass

from src.features.technical import FEATURE_COLUMNS, build_feature_frame, build_features
from src.ingest.market_data import load_daily_history
from src.models.train import train_final, train_holdout


@dataclass(frozen=True)
class Prediction:
    symbol: str
    as_of: str
    close_price: float
    probability_up: float
    probability_down: float
    signal: str
    holdout_accuracy: float
    holdout_brier: float
    labelled_rows: int

    def to_dict(self) -> dict:
        return asdict(self)


def predict_symbol(symbol: str, period: str = "5y") -> Prediction:
    symbol = symbol.upper().strip()
    if not symbol.endswith(".L"):
        raise ValueError("Use a London Stock Exchange symbol ending in .L, e.g. BARC.L")

    raw = load_daily_history(symbol, period=period)
    labelled = build_features(raw)
    live_features = build_feature_frame(raw)

    evaluation = train_holdout(labelled)
    final_model = train_final(labelled)

    latest = live_features.iloc[[-1]]
    probability_up = float(final_model.predict_proba(latest[FEATURE_COLUMNS])[:, 1][0])
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
        holdout_accuracy=round(evaluation.accuracy, 4),
        holdout_brier=round(evaluation.brier, 4),
        labelled_rows=len(labelled),
    )
