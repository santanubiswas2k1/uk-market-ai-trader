from src.models.factory import (
    DEFAULT_MODEL_WEIGHTS,
    DEFAULT_RETURN_MODEL_WEIGHTS,
    MODEL_NAMES,
    RETURN_MODEL_NAMES,
    make_model,
    make_return_model,
)


def test_ensemble_has_five_equal_weight_models():
    assert MODEL_NAMES == (
        "logistic_regression",
        "random_forest",
        "xgboost",
        "lightgbm",
        "catboost",
    )
    assert sum(DEFAULT_MODEL_WEIGHTS.values()) == 1.0
    assert all(weight == 0.2 for weight in DEFAULT_MODEL_WEIGHTS.values())


def test_all_ensemble_models_can_be_constructed():
    for name in MODEL_NAMES:
        assert make_model(name) is not None


def test_return_ensemble_has_five_equal_weight_models():
    assert RETURN_MODEL_NAMES == (
        "ridge",
        "random_forest",
        "xgboost",
        "lightgbm",
        "catboost",
    )
    assert sum(DEFAULT_RETURN_MODEL_WEIGHTS.values()) == 1.0
    assert all(weight == 0.2 for weight in DEFAULT_RETURN_MODEL_WEIGHTS.values())


def test_all_return_models_can_be_constructed():
    for name in RETURN_MODEL_NAMES:
        assert make_return_model(name) is not None
