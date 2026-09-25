from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss

from src.models.train import make_model


@dataclass(frozen=True)
class WalkForwardResult:
    predictions: pd.DataFrame
    accuracy: float
    brier: float
    folds: int


def walk_forward_evaluate(
    frame: pd.DataFrame,
    feature_columns: list[str],
    min_train_rows: int = 252,
    test_rows: int = 20,
    step_rows: int = 20,
) -> WalkForwardResult:
    """Expanding-window walk-forward evaluation.

    Each fold trains only on rows strictly earlier than its test window.
    """
    if len(frame) <= min_train_rows:
        raise ValueError("Not enough rows for walk-forward evaluation")

    outputs: list[pd.DataFrame] = []
    folds = 0

    start = min_train_rows
    while start < len(frame):
        end = min(start + test_rows, len(frame))
        train = frame.iloc[:start]
        test = frame.iloc[start:end]
        if test.empty:
            break

        model = make_model()
        model.fit(train[feature_columns], train["target_up_1d"])

        prob = model.predict_proba(test[feature_columns])[:, 1]
        fold = test[["target_up_1d"]].copy()
        fold["prob_up"] = prob
        fold["predicted_up"] = (prob >= 0.5).astype(int)
        outputs.append(fold)
        folds += 1
        start += step_rows

    predictions = pd.concat(outputs).sort_index()
    return WalkForwardResult(
        predictions=predictions,
        accuracy=float(accuracy_score(predictions["target_up_1d"], predictions["predicted_up"])),
        brier=float(brier_score_loss(predictions["target_up_1d"], predictions["prob_up"])),
        folds=folds,
    )
