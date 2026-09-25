from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import ClassifierMixin, RegressorMixin
from sklearn.metrics import accuracy_score, brier_score_loss

from src.models.factory import (
    DEFAULT_MODEL_WEIGHTS,
    DEFAULT_RETURN_MODEL_WEIGHTS,
    MODEL_NAMES,
    RETURN_MODEL_NAMES,
    make_model,
    make_return_model,
)


@dataclass(frozen=True)
class ModelMetrics:
    accuracy: float
    brier: float


@dataclass(frozen=True)
class EnsembleEvaluation:
    accuracy: float
    brier: float
    folds: int
    model_metrics: dict[str, ModelMetrics]


def _normalise_weights(weights: dict[str, float] | None = None) -> dict[str, float]:
    chosen = dict(weights or DEFAULT_MODEL_WEIGHTS)
    missing = set(MODEL_NAMES) - set(chosen)
    if missing:
        raise ValueError(f"Missing ensemble weights for: {sorted(missing)}")

    total = sum(float(chosen[name]) for name in MODEL_NAMES)
    if total <= 0:
        raise ValueError("Ensemble weights must sum to a positive value")

    return {name: float(chosen[name]) / total for name in MODEL_NAMES}


def train_final_ensemble(
    frame: pd.DataFrame,
    feature_columns: list[str],
) -> dict[str, ClassifierMixin]:
    if len(frame) < 50:
        raise ValueError("At least 50 labelled rows are required")

    models: dict[str, ClassifierMixin] = {}
    for name in MODEL_NAMES:
        model = make_model(name)
        model.fit(frame[feature_columns], frame["target_up_1d"])
        models[name] = model
    return models


def predict_ensemble(
    models: dict[str, ClassifierMixin],
    latest: pd.DataFrame,
    feature_columns: list[str],
    weights: dict[str, float] | None = None,
) -> tuple[dict[str, float], float]:
    normalised = _normalise_weights(weights)
    probabilities: dict[str, float] = {}

    for name in MODEL_NAMES:
        model = models[name]
        probabilities[name] = float(model.predict_proba(latest[feature_columns])[:, 1][0])

    combined = sum(probabilities[name] * normalised[name] for name in MODEL_NAMES)
    return probabilities, float(combined)


def walk_forward_ensemble(
    frame: pd.DataFrame,
    feature_columns: list[str],
    min_train_rows: int = 252,
    test_rows: int = 20,
    step_rows: int = 20,
    weights: dict[str, float] | None = None,
) -> EnsembleEvaluation:
    if len(frame) <= min_train_rows:
        raise ValueError("Not enough rows for walk-forward evaluation")

    normalised = _normalise_weights(weights)
    truth: list[int] = []
    combined_probabilities: list[float] = []
    per_model_probabilities: dict[str, list[float]] = {name: [] for name in MODEL_NAMES}
    folds = 0

    start = min_train_rows
    while start < len(frame):
        end = min(start + test_rows, len(frame))
        train = frame.iloc[:start]
        test = frame.iloc[start:end]
        if test.empty:
            break

        fold_probabilities: dict[str, np.ndarray] = {}
        for name in MODEL_NAMES:
            model = make_model(name)
            model.fit(train[feature_columns], train["target_up_1d"])
            probabilities = model.predict_proba(test[feature_columns])[:, 1]
            fold_probabilities[name] = probabilities
            per_model_probabilities[name].extend(float(value) for value in probabilities)

        combined = np.zeros(len(test), dtype=float)
        for name in MODEL_NAMES:
            combined += fold_probabilities[name] * normalised[name]

        truth.extend(int(value) for value in test["target_up_1d"])
        combined_probabilities.extend(float(value) for value in combined)
        folds += 1
        start += step_rows

    if not truth:
        raise ValueError("Walk-forward evaluation produced no predictions")

    y_true = np.asarray(truth)
    combined_prob = np.asarray(combined_probabilities)
    model_metrics: dict[str, ModelMetrics] = {}

    for name in MODEL_NAMES:
        probabilities = np.asarray(per_model_probabilities[name])
        predictions = (probabilities >= 0.5).astype(int)
        model_metrics[name] = ModelMetrics(
            accuracy=float(accuracy_score(y_true, predictions)),
            brier=float(brier_score_loss(y_true, probabilities)),
        )

    return EnsembleEvaluation(
        accuracy=float(accuracy_score(y_true, (combined_prob >= 0.5).astype(int))),
        brier=float(brier_score_loss(y_true, combined_prob)),
        folds=folds,
        model_metrics=model_metrics,
    )



def _normalise_return_weights(
    weights: dict[str, float] | None = None,
) -> dict[str, float]:
    chosen = dict(weights or DEFAULT_RETURN_MODEL_WEIGHTS)
    missing = set(RETURN_MODEL_NAMES) - set(chosen)
    if missing:
        raise ValueError(f"Missing return ensemble weights for: {sorted(missing)}")

    total = sum(float(chosen[name]) for name in RETURN_MODEL_NAMES)
    if total <= 0:
        raise ValueError("Return ensemble weights must sum to a positive value")

    return {
        name: float(chosen[name]) / total
        for name in RETURN_MODEL_NAMES
    }


def train_return_ensemble(
    frame: pd.DataFrame,
    feature_columns: list[str],
) -> dict[str, RegressorMixin]:
    if len(frame) < 50:
        raise ValueError("At least 50 labelled rows are required")

    models: dict[str, RegressorMixin] = {}
    for name in RETURN_MODEL_NAMES:
        model = make_return_model(name)
        model.fit(frame[feature_columns], frame["target_return_1d"])
        models[name] = model
    return models


def predict_return_ensemble(
    models: dict[str, RegressorMixin],
    latest: pd.DataFrame,
    feature_columns: list[str],
    weights: dict[str, float] | None = None,
) -> tuple[dict[str, float], float]:
    normalised = _normalise_return_weights(weights)
    predictions: dict[str, float] = {}

    for name in RETURN_MODEL_NAMES:
        model = models[name]
        predictions[name] = float(
            model.predict(latest[feature_columns])[0]
        )

    combined = sum(
        predictions[name] * normalised[name]
        for name in RETURN_MODEL_NAMES
    )
    return predictions, float(combined)
