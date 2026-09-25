from __future__ import annotations

import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "ret_1d",
    "ret_5d",
    "vol_10d",
    "ma_gap_10d",
    "volume_z_20d",
]


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Build model features without creating a label.

    Keeping feature construction separate from label construction prevents the
    newest observation from being accidentally assigned a false target.
    """
    out = df.copy().sort_index()

    out["ret_1d"] = out["close"].pct_change()
    out["ret_5d"] = out["close"].pct_change(5)
    out["vol_10d"] = out["ret_1d"].rolling(10).std() * np.sqrt(252)

    ma10 = out["close"].rolling(10).mean()
    out["ma_gap_10d"] = out["close"] / ma10 - 1

    vol_mean = out["volume"].rolling(20).mean()
    vol_std = out["volume"].rolling(20).std()
    out["volume_z_20d"] = (out["volume"] - vol_mean) / vol_std

    return out.dropna(subset=FEATURE_COLUMNS)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build labelled rows for next-day direction training."""
    out = build_feature_frame(df)
    next_close = out["close"].shift(-1)
    out["target_up_1d"] = (next_close > out["close"]).astype("Int64")
    out.loc[next_close.isna(), "target_up_1d"] = pd.NA
    out = out.dropna(subset=["target_up_1d"]).copy()
    out["target_up_1d"] = out["target_up_1d"].astype(int)
    return out
