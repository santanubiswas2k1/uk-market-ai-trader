from __future__ import annotations

from collections.abc import Callable

from catboost import CatBoostClassifier, CatBoostRegressor
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.base import ClassifierMixin, RegressorMixin
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor

MODEL_NAMES = (
    "logistic_regression",
    "random_forest",
    "xgboost",
    "lightgbm",
    "catboost",
)

DEFAULT_MODEL_WEIGHTS = {name: 1.0 / len(MODEL_NAMES) for name in MODEL_NAMES}


def _logistic_regression() -> ClassifierMixin:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    max_iter=1_000,
                    random_state=42,
                    class_weight="balanced",
                ),
            ),
        ]
    )


def _random_forest() -> ClassifierMixin:
    return RandomForestClassifier(
        n_estimators=150,
        max_depth=7,
        min_samples_leaf=5,
        class_weight="balanced_subsample",
        n_jobs=1,
        random_state=42,
    )


def _xgboost() -> ClassifierMixin:
    return XGBClassifier(
        n_estimators=160,
        max_depth=4,
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        n_jobs=1,
        random_state=42,
    )


def _lightgbm() -> ClassifierMixin:
    return LGBMClassifier(
        n_estimators=160,
        num_leaves=15,
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=1,
        random_state=42,
        verbosity=-1,
    )


def _catboost() -> ClassifierMixin:
    return CatBoostClassifier(
        iterations=160,
        depth=5,
        learning_rate=0.04,
        loss_function="Logloss",
        verbose=False,
        allow_writing_files=False,
        thread_count=1,
        random_seed=42,
    )


MODEL_FACTORIES: dict[str, Callable[[], ClassifierMixin]] = {
    "logistic_regression": _logistic_regression,
    "random_forest": _random_forest,
    "xgboost": _xgboost,
    "lightgbm": _lightgbm,
    "catboost": _catboost,
}


def make_model(name: str) -> ClassifierMixin:
    try:
        return MODEL_FACTORIES[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown model: {name}") from exc


RETURN_MODEL_NAMES = (
    "ridge",
    "random_forest",
    "xgboost",
    "lightgbm",
    "catboost",
)

DEFAULT_RETURN_MODEL_WEIGHTS = {
    name: 1.0 / len(RETURN_MODEL_NAMES) for name in RETURN_MODEL_NAMES
}


def _ridge_regressor() -> RegressorMixin:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            ("model", Ridge(alpha=1.0)),
        ]
    )


def _random_forest_regressor() -> RegressorMixin:
    return RandomForestRegressor(
        n_estimators=150,
        max_depth=7,
        min_samples_leaf=5,
        n_jobs=1,
        random_state=42,
    )


def _xgboost_regressor() -> RegressorMixin:
    return XGBRegressor(
        n_estimators=160,
        max_depth=4,
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        n_jobs=1,
        random_state=42,
    )


def _lightgbm_regressor() -> RegressorMixin:
    return LGBMRegressor(
        n_estimators=160,
        num_leaves=15,
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=1,
        random_state=42,
        verbosity=-1,
    )


def _catboost_regressor() -> RegressorMixin:
    return CatBoostRegressor(
        iterations=160,
        depth=5,
        learning_rate=0.04,
        loss_function="RMSE",
        verbose=False,
        allow_writing_files=False,
        thread_count=1,
        random_seed=42,
    )


RETURN_MODEL_FACTORIES: dict[str, Callable[[], RegressorMixin]] = {
    "ridge": _ridge_regressor,
    "random_forest": _random_forest_regressor,
    "xgboost": _xgboost_regressor,
    "lightgbm": _lightgbm_regressor,
    "catboost": _catboost_regressor,
}


def make_return_model(name: str) -> RegressorMixin:
    try:
        return RETURN_MODEL_FACTORIES[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown return model: {name}") from exc
