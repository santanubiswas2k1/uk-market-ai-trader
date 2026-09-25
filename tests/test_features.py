import pandas as pd

from src.features.technical import FEATURE_COLUMNS, build_features


def test_build_features_creates_expected_columns():
    idx = pd.date_range("2025-01-01", periods=40, freq="B", tz="UTC")
    df = pd.DataFrame(
        {
            "close": [100 + i * 0.2 for i in range(40)],
            "volume": [1_000_000 + i * 10_000 for i in range(40)],
        },
        index=idx,
    )

    out = build_features(df)
    for column in FEATURE_COLUMNS:
        assert column in out.columns
    assert "target_up_1d" in out.columns
