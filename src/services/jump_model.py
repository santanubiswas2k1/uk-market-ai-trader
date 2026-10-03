from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
)
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.ingest.market_data import load_universe_history

JUMP_HORIZON_DAYS = 3
JUMP_THRESHOLD = 0.05
MODEL_VERSION = "jump_3d_5pct_v1"
MODEL_CACHE_TTL = timedelta(hours=6)

# Liquid US names provide a practical first universe while the cross-sectional
# model and forward evaluation are proved. The universe can be broadened once
# the data source is upgraded from the research-grade Yahoo adapter.
US_JUMP_UNIVERSE: tuple[str, ...] = (
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
    "META",
    "TSLA",
    "AMD",
    "NFLX",
    "AVGO",
    "ORCL",
    "CRM",
    "ADBE",
    "QCOM",
    "INTC",
    "JPM",
    "BAC",
    "GS",
    "V",
    "MA",
    "WMT",
    "COST",
    "HD",
    "NKE",
    "KO",
    "PEP",
    "XOM",
    "CVX",
    "LLY",
    "UNH",
    "JNJ",
    "ABBV",
    "MRK",
    "CAT",
    "GE",
    "BA",
    "PLTR",
    "COIN",
    "UBER",
    "SHOP",
)

FEATURE_COLUMNS = (
    "return_1d",
    "return_3d",
    "return_5d",
    "return_10d",
    "volume_ratio_20d",
    "volume_acceleration",
    "volatility_5d",
    "volatility_ratio",
    "range_position_20d",
    "distance_to_20d_high",
    "ma_gap_10d",
    "ma_gap_20d",
    "atr_pct_14",
    "atr_expansion",
)


@dataclass(frozen=True)
class JumpCandidate:
    symbol: str
    probability_jump_3d_5pct: float
    expected_max_return_3d: float
    expected_adverse_return_3d: float
    last_close: float
    return_1d: float
    return_5d: float
    volume_ratio_20d: float
    volatility_ratio: float
    distance_to_20d_high: float
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class _ModelBundle:
    trained_at: datetime
    classifiers: tuple[object, ...]
    calibrator: IsotonicRegression | None
    upside_model: HistGradientBoostingRegressor
    downside_model: HistGradientBoostingRegressor
    validation: dict[str, float | int]
    training_rows: int
    symbols_used: int


_model_bundle: _ModelBundle | None = None
_model_lock = Lock()


def _feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"close", "high", "low", "volume"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing market-data columns: {sorted(missing)}")

    close = frame["close"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    volume = frame["volume"].astype(float).fillna(0.0)
    returns = close.pct_change()

    features = pd.DataFrame(index=frame.index)
    features["return_1d"] = close.pct_change(1)
    features["return_3d"] = close.pct_change(3)
    features["return_5d"] = close.pct_change(5)
    features["return_10d"] = close.pct_change(10)

    volume_mean_20 = volume.shift(1).rolling(20).mean()
    volume_mean_5 = volume.shift(1).rolling(5).mean()
    features["volume_ratio_20d"] = volume / volume_mean_20.replace(0.0, np.nan)
    features["volume_acceleration"] = (
        volume_mean_5 / volume_mean_20.replace(0.0, np.nan) - 1.0
    )

    vol_5 = returns.rolling(5).std()
    vol_20 = returns.rolling(20).std()
    features["volatility_5d"] = vol_5
    features["volatility_ratio"] = vol_5 / vol_20.replace(0.0, np.nan)

    prior_high_20 = high.shift(1).rolling(20).max()
    prior_low_20 = low.shift(1).rolling(20).min()
    price_span = (prior_high_20 - prior_low_20).replace(0.0, np.nan)
    features["range_position_20d"] = (close - prior_low_20) / price_span
    features["distance_to_20d_high"] = close / prior_high_20 - 1.0

    features["ma_gap_10d"] = close / close.rolling(10).mean() - 1.0
    features["ma_gap_20d"] = close / close.rolling(20).mean() - 1.0

    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr_14 = true_range.rolling(14).mean()
    features["atr_pct_14"] = atr_14 / close.replace(0.0, np.nan)
    features["atr_expansion"] = (
        true_range.rolling(5).mean()
        / true_range.rolling(20).mean().replace(0.0, np.nan)
    )

    return features.replace([np.inf, -np.inf], np.nan)


def _training_rows(symbol: str, frame: pd.DataFrame) -> pd.DataFrame:
    features = _feature_frame(frame)
    close = frame["close"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)

    future_highs = pd.concat(
        [high.shift(-step) for step in range(1, JUMP_HORIZON_DAYS + 1)],
        axis=1,
    )
    future_lows = pd.concat(
        [low.shift(-step) for step in range(1, JUMP_HORIZON_DAYS + 1)],
        axis=1,
    )

    rows = features.copy()
    rows["future_max_return_3d"] = future_highs.max(axis=1) / close - 1.0
    rows["future_min_return_3d"] = future_lows.min(axis=1) / close - 1.0
    rows["jump_target"] = (
        rows["future_max_return_3d"] >= JUMP_THRESHOLD
    ).astype(int)
    rows["symbol"] = symbol
    rows["date"] = rows.index

    # The last horizon rows have incomplete labels and must never enter training.
    rows.iloc[-JUMP_HORIZON_DAYS:, rows.columns.get_loc("future_max_return_3d")] = np.nan
    rows.iloc[-JUMP_HORIZON_DAYS:, rows.columns.get_loc("future_min_return_3d")] = np.nan

    return rows.dropna(
        subset=[
            *FEATURE_COLUMNS,
            "future_max_return_3d",
            "future_min_return_3d",
        ]
    )


def _balanced_weights(target: np.ndarray) -> np.ndarray:
    positives = max(int(target.sum()), 1)
    negatives = max(len(target) - positives, 1)
    positive_weight = len(target) / (2.0 * positives)
    negative_weight = len(target) / (2.0 * negatives)
    return np.where(target == 1, positive_weight, negative_weight)


def _fit_bundle(histories: dict[str, pd.DataFrame]) -> _ModelBundle:
    frames = [
        _training_rows(symbol, frame)
        for symbol, frame in histories.items()
        if frame is not None and not frame.empty and len(frame) >= 80
    ]
    if not frames:
        raise ValueError("Not enough US history to train the jump model")

    dataset = pd.concat(frames, ignore_index=True).sort_values("date")
    if len(dataset) < 800:
        raise ValueError("Not enough cross-sectional rows to train the jump model")

    split_index = int(len(dataset) * 0.8)
    split_index = max(500, min(split_index, len(dataset) - 150))
    train = dataset.iloc[:split_index]
    validation = dataset.iloc[split_index:]

    x_train = train.loc[:, FEATURE_COLUMNS].to_numpy(dtype=float)
    y_train = train["jump_target"].to_numpy(dtype=int)
    x_validation = validation.loc[:, FEATURE_COLUMNS].to_numpy(dtype=float)
    y_validation = validation["jump_target"].to_numpy(dtype=int)
    sample_weight = _balanced_weights(y_train)

    logistic = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            max_iter=500,
            class_weight="balanced",
            random_state=42,
        ),
    )
    random_forest = RandomForestClassifier(
        n_estimators=220,
        max_depth=8,
        min_samples_leaf=8,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=42,
    )
    histogram = HistGradientBoostingClassifier(
        max_iter=180,
        max_depth=5,
        learning_rate=0.06,
        l2_regularization=1.0,
        random_state=42,
    )

    logistic.fit(x_train, y_train)
    random_forest.fit(x_train, y_train)
    histogram.fit(x_train, y_train, sample_weight=sample_weight)
    classifiers: tuple[object, ...] = (logistic, random_forest, histogram)

    raw_validation = np.mean(
        [model.predict_proba(x_validation)[:, 1] for model in classifiers],
        axis=0,
    )

    calibrator: IsotonicRegression | None = None
    if len(np.unique(y_validation)) == 2 and int(y_validation.sum()) >= 20:
        calibrator = IsotonicRegression(out_of_bounds="clip")
        calibrator.fit(raw_validation, y_validation)
        calibrated_validation = calibrator.predict(raw_validation)
    else:
        calibrated_validation = raw_validation

    upside_model = HistGradientBoostingRegressor(
        max_iter=160,
        max_depth=5,
        learning_rate=0.06,
        l2_regularization=1.0,
        random_state=43,
    )
    downside_model = HistGradientBoostingRegressor(
        max_iter=160,
        max_depth=5,
        learning_rate=0.06,
        l2_regularization=1.0,
        random_state=44,
    )
    upside_model.fit(
        x_train,
        train["future_max_return_3d"].clip(-0.15, 0.35).to_numpy(dtype=float),
    )
    downside_model.fit(
        x_train,
        train["future_min_return_3d"].clip(-0.35, 0.15).to_numpy(dtype=float),
    )

    top_count = max(1, int(len(validation) * 0.1))
    top_indices = np.argsort(calibrated_validation)[-top_count:]
    validation_precision_top_decile = float(y_validation[top_indices].mean())

    return _ModelBundle(
        trained_at=datetime.now(UTC),
        classifiers=classifiers,
        calibrator=calibrator,
        upside_model=upside_model,
        downside_model=downside_model,
        validation={
            "rows": int(len(validation)),
            "base_jump_rate": round(float(y_validation.mean()), 6),
            "brier_score": round(
                float(brier_score_loss(y_validation, calibrated_validation)),
                6,
            ),
            "precision_top_decile": round(validation_precision_top_decile, 6),
        },
        training_rows=int(len(train)),
        symbols_used=len(frames),
    )


def _get_bundle(histories: dict[str, pd.DataFrame]) -> _ModelBundle:
    global _model_bundle

    now = datetime.now(UTC)
    if _model_bundle and now - _model_bundle.trained_at < MODEL_CACHE_TTL:
        return _model_bundle

    with _model_lock:
        if _model_bundle and now - _model_bundle.trained_at < MODEL_CACHE_TTL:
            return _model_bundle
        _model_bundle = _fit_bundle(histories)
        return _model_bundle


def _candidate_reasons(row: pd.Series) -> tuple[str, ...]:
    reasons: list[str] = []
    if row["volume_ratio_20d"] >= 1.5:
        reasons.append("unusual volume")
    if row["volume_acceleration"] >= 0.25:
        reasons.append("volume accelerating")
    if row["volatility_ratio"] >= 1.25:
        reasons.append("volatility expanding")
    if row["distance_to_20d_high"] >= -0.02:
        reasons.append("near 20-day high")
    if row["return_5d"] >= 0.04:
        reasons.append("strong 5-day momentum")
    if row["atr_expansion"] >= 1.2:
        reasons.append("range expansion")
    if not reasons:
        reasons.append("model pattern match")
    return tuple(reasons)


def scan_us_jumps(limit: int = 10) -> dict:
    requested = max(1, min(int(limit), 25))
    histories = load_universe_history(US_JUMP_UNIVERSE, period="2y")
    if not histories:
        raise ValueError("US market history is unavailable")

    bundle = _get_bundle(histories)
    candidates: list[JumpCandidate] = []
    failures: list[str] = []

    for symbol in US_JUMP_UNIVERSE:
        frame = histories.get(symbol)
        if frame is None or frame.empty:
            failures.append(symbol)
            continue

        try:
            features = _feature_frame(frame).dropna(subset=list(FEATURE_COLUMNS))
            if features.empty:
                failures.append(symbol)
                continue

            latest = features.iloc[-1]
            x_latest = latest.loc[list(FEATURE_COLUMNS)].to_numpy(dtype=float).reshape(1, -1)
            raw_probability = float(
                np.mean(
                    [
                        model.predict_proba(x_latest)[0, 1]
                        for model in bundle.classifiers
                    ]
                )
            )
            probability = (
                float(bundle.calibrator.predict([raw_probability])[0])
                if bundle.calibrator is not None
                else raw_probability
            )

            expected_upside = float(bundle.upside_model.predict(x_latest)[0])
            expected_downside = float(bundle.downside_model.predict(x_latest)[0])
            last_close = float(frame["close"].iloc[-1])

            candidates.append(
                JumpCandidate(
                    symbol=symbol,
                    probability_jump_3d_5pct=round(max(0.0, min(1.0, probability)), 6),
                    expected_max_return_3d=round(expected_upside, 6),
                    expected_adverse_return_3d=round(expected_downside, 6),
                    last_close=round(last_close, 4),
                    return_1d=round(float(latest["return_1d"]), 6),
                    return_5d=round(float(latest["return_5d"]), 6),
                    volume_ratio_20d=round(float(latest["volume_ratio_20d"]), 3),
                    volatility_ratio=round(float(latest["volatility_ratio"]), 3),
                    distance_to_20d_high=round(float(latest["distance_to_20d_high"]), 6),
                    reasons=_candidate_reasons(latest),
                )
            )
        except (KeyError, ValueError, ZeroDivisionError, FloatingPointError):
            failures.append(symbol)

    candidates.sort(
        key=lambda item: (
            item.probability_jump_3d_5pct,
            item.expected_max_return_3d,
        ),
        reverse=True,
    )

    return {
        "market": "us",
        "objective": "Probability of reaching +5% within the next 3 trading sessions",
        "model_version": MODEL_VERSION,
        "threshold": JUMP_THRESHOLD,
        "horizon_trading_days": JUMP_HORIZON_DAYS,
        "probabilities_calibrated": bundle.calibrator is not None,
        "trained_at": bundle.trained_at.isoformat(),
        "training_rows": bundle.training_rows,
        "symbols_used_for_training": bundle.symbols_used,
        "universe_size": len(US_JUMP_UNIVERSE),
        "scanned": len(candidates),
        "failed_symbols": failures,
        "validation": bundle.validation,
        "candidates": [candidate.to_dict() for candidate in candidates[:requested]],
    }
