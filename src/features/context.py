from __future__ import annotations

import pandas as pd

from src.features.technical import FEATURE_COLUMNS, build_feature_frame

MARKET_FEATURE_COLUMNS = [
    "market_ret_1d",
    "market_ret_5d",
    "fx_ret_1d",
    "fx_ret_5d",
    "market_rel_1d",
    "sector_ret_1d",
    "sector_ret_5d",
    "sector_rel_1d",
    "vix_ret_1d",
    "us10y_ret_1d",
    "oil_ret_1d",
    "gold_ret_1d",
]

ENRICHED_FEATURE_COLUMNS = FEATURE_COLUMNS + MARKET_FEATURE_COLUMNS


def build_enriched_feature_frame(
    stock: pd.DataFrame,
    market_context: pd.DataFrame,
    rns_daily: pd.DataFrame | None = None,
    macro_daily: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Join technical, market, sector and risk features without look-ahead."""
    out = build_feature_frame(stock).copy()

    context = market_context.copy().sort_index()
    context["market_ret_1d"] = context["market_close"].pct_change()
    context["market_ret_5d"] = context["market_close"].pct_change(5)
    context["fx_ret_1d"] = context["fx_close"].pct_change()
    context["fx_ret_5d"] = context["fx_close"].pct_change(5)
    context["sector_ret_1d"] = context["sector_close"].pct_change()
    context["sector_ret_5d"] = context["sector_close"].pct_change(5)
    context["vix_ret_1d"] = context["vix_close"].pct_change()
    context["us10y_ret_1d"] = context["us10y_close"].pct_change()
    context["oil_ret_1d"] = context["oil_close"].pct_change()
    context["gold_ret_1d"] = context["gold_close"].pct_change()

    join_columns = [
        "market_ret_1d",
        "market_ret_5d",
        "fx_ret_1d",
        "fx_ret_5d",
        "sector_ret_1d",
        "sector_ret_5d",
        "vix_ret_1d",
        "us10y_ret_1d",
        "oil_ret_1d",
        "gold_ret_1d",
    ]
    out = out.join(context[join_columns], how="left")
    out["market_rel_1d"] = out["ret_1d"] - out["market_ret_1d"]
    out["sector_rel_1d"] = out["ret_1d"] - out["sector_ret_1d"]

    if rns_daily is not None:
        rns = rns_daily.copy().sort_index()
        out = out.join(rns, how="left")
        rns_cols = [c for c in rns.columns if c.startswith("rns_")]
        out[rns_cols] = out[rns_cols].fillna(0.0)

    if macro_daily is not None:
        macro = macro_daily.copy().sort_index()
        out = out.join(macro, how="left")
        out[macro.columns] = out[macro.columns].ffill()

    return out.dropna(subset=ENRICHED_FEATURE_COLUMNS)


def build_enriched_features(
    stock: pd.DataFrame,
    market_context: pd.DataFrame,
    rns_daily: pd.DataFrame | None = None,
    macro_daily: pd.DataFrame | None = None,
) -> pd.DataFrame:
    out = build_enriched_feature_frame(stock, market_context, rns_daily, macro_daily)
    next_close = out["close"].shift(-1)
    out["target_up_1d"] = (next_close > out["close"]).astype("Int64")
    out.loc[next_close.isna(), "target_up_1d"] = pd.NA
    out = out.dropna(subset=["target_up_1d"]).copy()
    out["target_up_1d"] = out["target_up_1d"].astype(int)
    return out
