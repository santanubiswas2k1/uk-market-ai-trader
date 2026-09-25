from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss
from xgboost import XGBClassifier

from src.features.technical import FEATURE_COLUMNS


@dataclass
class TrainResult:
    model: XGBClassifier
    accuracy: float
    brier: float
    rows_train: int
    rows_test: int


def make_model() -> XGBClassifier:
    return XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
    )


def train_holdout(feature_frame: pd.DataFrame, test_fraction: float = 0.2) -> TrainResult:
    """Evaluate using a chronological holdout rather than a random split."""
    if not 0 < test_fraction < 0.5:
        raise ValueError("test_fraction must be between 0 and 0.5")
    if len(feature_frame) < 50:
        raise ValueError("At least 50 labelled rows are required")

    split = int(len(feature_frame) * (1 - test_fraction))
    train = feature_frame.iloc[:split]
    test = feature_frame.iloc[split:]

    model = make_model()
    model.fit(train[FEATURE_COLUMNS], train["target_up_1d"])

    prob = model.predict_proba(test[FEATURE_COLUMNS])[:, 1]
    pred = (prob >= 0.5).astype(int)

    return TrainResult(
        model=model,
        accuracy=float(accuracy_score(test["target_up_1d"], pred)),
        brier=float(brier_score_loss(test["target_up_1d"], prob)),
        rows_train=len(train),
        rows_test=len(test),
    )


def train_final(feature_frame: pd.DataFrame) -> XGBClassifier:
    """Train the production research model on every currently labelled row."""
    if len(feature_frame) < 50:
        raise ValueError("At least 50 labelled rows are required")
    model = make_model()
    model.fit(feature_frame[FEATURE_COLUMNS], feature_frame["target_up_1d"])
    return model
