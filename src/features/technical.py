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


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().sort_index()

    out["ret_1d"] = out["close"].pct_change()
    out["ret_5d"] = out["close"].pct_change(5)
    out["vol_10d"] = out["ret_1d"].rolling(10).std() * np.sqrt(252)

    ma10 = out["close"].rolling(10).mean()
    out["ma_gap_10d"] = out["close"] / ma10 - 1

    vol_mean = out["volume"].rolling(20).mean()
    vol_std = out["volume"].rolling(20).std()
    out["volume_z_20d"] = (out["volume"] - vol_mean) / vol_std

    out["target_up_1d"] = (out["close"].shift(-1) > out["close"]).astype(int)

    return out.dropna(subset=FEATURE_COLUMNS + ["target_up_1d"])
