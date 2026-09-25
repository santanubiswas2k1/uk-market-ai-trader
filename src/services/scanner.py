from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite

import numpy as np
import pandas as pd

from src.ingest.market_data import load_daily_history
from src.ingest.news import load_live_decision_context
from src.markets import get_market

SCAN_UNIVERSES: dict[str, tuple[str, ...]] = {
    "uk": (
        "BARC.L",
        "LLOY.L",
        "SHEL.L",
        "AZN.L",
        "BP.L",
        "GSK.L",
        "HSBA.L",
        "RR.L",
        "ULVR.L",
        "NG.L",
    ),
    "us": (
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "GOOGL",
        "META",
        "TSLA",
        "AMD",
        "NFLX",
        "JPM",
    ),
    "india": (
        "RELIANCE.NS",
        "TCS.NS",
        "INFY.NS",
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "BHARTIARTL.NS",
        "LT.NS",
        "ITC.NS",
        "AXISBANK.NS",
    ),
    "uae": (
        "EMAAR.DU",
        "DEWA.DU",
        "FAB.AE",
        "ADCB.AE",
        "ALDAR.AE",
        "IHC.AE",
    ),
    "canada": (
        "RY.TO",
        "TD.TO",
        "SHOP.TO",
        "ENB.TO",
        "BNS.TO",
        "CNR.TO",
        "CNQ.TO",
        "SU.TO",
        "BMO.TO",
        "CP.TO",
    ),
    "europe": (
        "SAP.DE",
        "ASML.AS",
        "MC.PA",
        "SIE.DE",
        "OR.PA",
        "AIR.PA",
        "TTE.PA",
        "SAN.MC",
        "ADS.DE",
        "BNP.PA",
    ),
    "hong_kong": (
        "0700.HK",
        "9988.HK",
        "0005.HK",
        "1299.HK",
        "3690.HK",
        "2318.HK",
        "1810.HK",
        "0388.HK",
    ),
    "japan": (
        "7203.T",
        "6758.T",
        "9984.T",
        "8306.T",
        "6501.T",
        "7974.T",
        "8035.T",
        "6861.T",
    ),
    "australia": (
        "BHP.AX",
        "CBA.AX",
        "CSL.AX",
        "NAB.AX",
        "WBC.AX",
        "ANZ.AX",
        "WES.AX",
        "MQG.AX",
    ),
}


@dataclass(frozen=True)
class ScannerCandidate:
    symbol: str
    market: str
    score: int
    activity: str
    last_close: float
    return_1d: float
    return_5d: float
    volume_ratio_20d: float
    volatility_ratio: float
    breakout_score: float
    range_position_20d: float
    news_count_24h: int
    news_sentiment: float
    earnings_within_7d: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _safe_float(value: float | np.floating | None, default: float = 0.0) -> float:
    if value is None:
        return default
    number = float(value)
    return number if isfinite(number) else default


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _technical_snapshot(frame: pd.DataFrame) -> dict[str, float]:
    if len(frame) < 25:
        raise ValueError("At least 25 daily rows are required for scanning")

    close = frame["close"].astype(float)
    volume = frame["volume"].astype(float).fillna(0.0)
    returns = close.pct_change()

    latest_close = _safe_float(close.iloc[-1])
    return_1d = _safe_float(close.iloc[-1] / close.iloc[-2] - 1.0)
    return_5d = _safe_float(close.iloc[-1] / close.iloc[-6] - 1.0)

    mean_volume = _safe_float(volume.iloc[-21:-1].mean())
    volume_ratio = _safe_float(volume.iloc[-1] / mean_volume if mean_volume > 0 else 0.0)

    recent_vol = _safe_float(returns.iloc[-5:].std())
    baseline_vol = _safe_float(returns.iloc[-25:-5].std())
    volatility_ratio = _safe_float(
        recent_vol / baseline_vol if baseline_vol > 0 else 1.0,
        default=1.0,
    )

    previous_window = close.iloc[-21:-1]
    prior_high = _safe_float(previous_window.max(), latest_close)
    prior_low = _safe_float(previous_window.min(), latest_close)
    span = max(prior_high - prior_low, 1e-12)
    range_position = _clip01((latest_close - prior_low) / span)

    breakout_distance = 0.0
    if latest_close > prior_high:
        breakout_distance = (latest_close / prior_high) - 1.0
    elif latest_close < prior_low:
        breakout_distance = (prior_low / latest_close) - 1.0

    breakout_score = _clip01(
        max(
            breakout_distance / 0.03,
            abs(range_position - 0.5) * 1.4,
        )
    )

    return {
        "last_close": latest_close,
        "return_1d": return_1d,
        "return_5d": return_5d,
        "volume_ratio_20d": volume_ratio,
        "volatility_ratio": volatility_ratio,
        "breakout_score": breakout_score,
        "range_position_20d": range_position,
    }


def _score_candidate(
    symbol: str,
    market: str,
    technical: dict[str, float],
    context: dict,
) -> ScannerCandidate:
    volume_component = 20.0 * _clip01((technical["volume_ratio_20d"] - 1.0) / 1.5)
    volatility_component = 15.0 * _clip01((technical["volatility_ratio"] - 1.0) / 1.0)
    breakout_component = 15.0 * technical["breakout_score"]
    momentum_component = 10.0 * _clip01(
        max(
            abs(technical["return_1d"]) / 0.04,
            abs(technical["return_5d"]) / 0.08,
        )
    )
    range_component = 10.0 * _clip01(
        abs(technical["range_position_20d"] - 0.5) * 2.0
    )

    news_count = max(0, int(context.get("news_count_24h") or 0))
    news_sentiment = _safe_float(context.get("news_sentiment"))
    news_component = 15.0 * _clip01(
        (min(news_count, 5) / 5.0) * 0.7 + abs(news_sentiment) * 0.3
    )

    earnings_within_7d = bool(context.get("earnings_within_7d"))
    earnings_component = 10.0 if earnings_within_7d else 0.0

    gap_proxy_component = 5.0 * _clip01(abs(technical["return_1d"]) / 0.025)

    raw_score = (
        volume_component
        + volatility_component
        + breakout_component
        + momentum_component
        + range_component
        + news_component
        + earnings_component
        + gap_proxy_component
    )
    score = round(max(0.0, min(100.0, raw_score)))

    reasons: list[str] = []
    if technical["volume_ratio_20d"] >= 1.5:
        reasons.append("unusual volume")
    if technical["volatility_ratio"] >= 1.35:
        reasons.append("volatility expanding")
    if technical["breakout_score"] >= 0.65:
        reasons.append("near/beyond 20-day range")
    if abs(technical["return_5d"]) >= 0.04:
        reasons.append("strong 5-day momentum")
    if news_count >= 2:
        reasons.append("recent company news")
    if abs(news_sentiment) >= 0.5:
        reasons.append("strong news sentiment")
    if earnings_within_7d:
        reasons.append("earnings within 7 days")
    if not reasons:
        reasons.append("normal activity")

    if score >= 75:
        activity = "Very High"
    elif score >= 60:
        activity = "High"
    elif score >= 40:
        activity = "Moderate"
    else:
        activity = "Normal"

    return ScannerCandidate(
        symbol=symbol,
        market=market,
        score=score,
        activity=activity,
        last_close=round(technical["last_close"], 4),
        return_1d=round(technical["return_1d"], 6),
        return_5d=round(technical["return_5d"], 6),
        volume_ratio_20d=round(technical["volume_ratio_20d"], 3),
        volatility_ratio=round(technical["volatility_ratio"], 3),
        breakout_score=round(technical["breakout_score"], 3),
        range_position_20d=round(technical["range_position_20d"], 3),
        news_count_24h=news_count,
        news_sentiment=round(news_sentiment, 3),
        earnings_within_7d=earnings_within_7d,
        reasons=tuple(reasons),
    )


def scan_market(market: str, limit: int = 10) -> dict:
    config = get_market(market)
    universe = SCAN_UNIVERSES.get(config.key, (config.default_symbol,))
    candidates: list[ScannerCandidate] = []
    failures: list[str] = []

    for symbol in universe:
        try:
            history = load_daily_history(symbol, period="6mo")
            technical = _technical_snapshot(history)
            try:
                context = load_live_decision_context(symbol)
            except Exception:  # noqa: BLE001
                context = {}
            candidates.append(
                _score_candidate(
                    symbol=symbol,
                    market=config.key,
                    technical=technical,
                    context=context,
                )
            )
        except (ValueError, KeyError, ZeroDivisionError):
            failures.append(symbol)

    candidates.sort(key=lambda item: item.score, reverse=True)
    requested = max(1, min(int(limit), len(candidates) or 1))

    return {
        "market": config.key,
        "market_label": config.label,
        "universe_size": len(universe),
        "scanned": len(candidates),
        "failed_symbols": failures,
        "method": "rule_based_movement_score_v1",
        "score_is_directional": False,
        "candidates": [item.to_dict() for item in candidates[:requested]],
    }
