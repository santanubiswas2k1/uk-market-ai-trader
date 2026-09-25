from __future__ import annotations

import pandas as pd


def probability_strategy(
    df: pd.DataFrame,
    prob_col: str = "prob_up",
    threshold: float = 0.60,
    transaction_cost_bps: float = 10.0,
) -> pd.DataFrame:
    """Simple long/cash research backtest with transaction costs."""
    out = df.copy()
    out["position"] = (out[prob_col] >= threshold).astype(int)
    out["next_return"] = out["close"].pct_change().shift(-1)

    turnover = out["position"].diff().abs().fillna(out["position"])
    cost = turnover * (transaction_cost_bps / 10_000)

    out["strategy_return"] = out["position"] * out["next_return"] - cost
    out["equity_curve"] = (1 + out["strategy_return"].fillna(0)).cumprod()
    return out
