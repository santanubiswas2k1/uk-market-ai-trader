import pandas as pd

from src.features.context import ENRICHED_FEATURE_COLUMNS, build_enriched_feature_frame


def test_enriched_features_add_market_context():
    idx = pd.date_range("2024-01-01", periods=80, freq="B", tz="UTC")
    stock = pd.DataFrame(
        {
            "close": [100 + i * 0.2 for i in range(80)],
            "volume": [1_000_000 + i * 1000 for i in range(80)],
        },
        index=idx,
    )
    context = pd.DataFrame(
        {
            "market_close": [7500 + i for i in range(80)],
            "fx_close": [1.25 + i * 0.0001 for i in range(80)],
        },
        index=idx,
    )

    out = build_enriched_feature_frame(stock, context)
    for column in ENRICHED_FEATURE_COLUMNS:
        assert column in out.columns
    assert out.index[-1] == idx[-1]
