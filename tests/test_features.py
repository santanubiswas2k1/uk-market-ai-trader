import pandas as pd

from src.features.technical import FEATURE_COLUMNS, build_feature_frame, build_features


def _frame(rows: int = 60) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=rows, freq="B", tz="UTC")
    return pd.DataFrame(
        {
            "close": [100 + i * 0.2 for i in range(rows)],
            "volume": [1_000_000 + i * 10_000 for i in range(rows)],
        },
        index=idx,
    )


def test_build_feature_frame_keeps_latest_unlabelled_observation():
    raw = _frame()
    feature_frame = build_feature_frame(raw)
    assert feature_frame.index[-1] == raw.index[-1]
    for column in FEATURE_COLUMNS:
        assert column in feature_frame.columns


def test_build_features_drops_only_unlabelled_latest_feature_row():
    raw = _frame()
    feature_frame = build_feature_frame(raw)
    labelled = build_features(raw)
    assert len(labelled) == len(feature_frame) - 1
    assert labelled["target_up_1d"].isin([0, 1]).all()
