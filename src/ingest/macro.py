from __future__ import annotations

import pandas as pd


def normalize_macro_series(
    frame: pd.DataFrame,
    date_col: str = "date",
    value_col: str = "value",
    output_name: str = "boe_base_rate",
) -> pd.DataFrame:
    """Normalize a dated UK macro series such as Bank Rate or CPI.

    Pass data obtained from a permitted/official source. Values are forward-filled
    only after their observation date; callers must ensure release dates are used
    when publication lag matters.
    """
    if date_col not in frame or value_col not in frame:
        raise ValueError(f"Expected columns {date_col!r} and {value_col!r}")

    out = frame[[date_col, value_col]].copy()
    out[date_col] = pd.to_datetime(out[date_col], utc=True)
    out = out.dropna().drop_duplicates(subset=[date_col], keep="last")
    out = out.set_index(date_col).sort_index()
    out = out.rename(columns={value_col: output_name})
    return out
