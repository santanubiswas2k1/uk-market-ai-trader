from __future__ import annotations

import numpy as np
import pandas as pd

from src.services.jump_model import FEATURE_COLUMNS, _feature_frame, _training_rows


def _history(rows: int = 80) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="B", tz="UTC")
    close = np.linspace(100.0, 108.0, rows)
    frame = pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.8,
            "low": close - 0.8,
            "close": close,
            "adj close": close,
            "volume": np.linspace(1_000_000, 1_500_000, rows),
        },
        index=index,
    )
    return frame


def test_feature_frame_produces_latest_model_features() -> None:
    features = _feature_frame(_history()).dropna(subset=list(FEATURE_COLUMNS))

    assert not features.empty
    assert set(FEATURE_COLUMNS).issubset(features.columns)
    assert np.isfinite(features.iloc[-1][list(FEATURE_COLUMNS)].to_numpy(dtype=float)).all()


def test_jump_target_uses_future_three_session_high() -> None:
    frame = _history()
    target_position = 55
    target_close = float(frame["close"].iloc[target_position])
    frame.iloc[target_position + 2, frame.columns.get_loc("high")] = target_close * 1.06

    rows = _training_rows("TEST", frame)
    target_date = frame.index[target_position]
    target_row = rows.loc[rows["date"] == target_date].iloc[0]

    assert target_row["jump_target"] == 1
    assert target_row["future_max_return_3d"] >= 0.05


def test_training_excludes_incomplete_future_horizon() -> None:
    frame = _history()
    rows = _training_rows("TEST", frame)

    assert frame.index[-1] not in set(rows["date"])
    assert frame.index[-2] not in set(rows["date"])
    assert frame.index[-3] not in set(rows["date"])
