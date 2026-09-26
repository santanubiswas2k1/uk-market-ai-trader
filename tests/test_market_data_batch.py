import pandas as pd

from src.ingest.market_data import _extract_universe_frames


def _index() -> pd.DatetimeIndex:
    return pd.date_range("2026-01-01", periods=3, freq="B", tz="UTC")


def test_extract_universe_frames_with_ticker_first_columns():
    columns = pd.MultiIndex.from_tuples(
        [
            ("AAPL", "Close"),
            ("AAPL", "Volume"),
            ("MSFT", "Close"),
            ("MSFT", "Volume"),
        ]
    )
    frame = pd.DataFrame(
        [
            [100.0, 10.0, 200.0, 20.0],
            [101.0, 11.0, 201.0, 21.0],
            [102.0, 12.0, 202.0, 22.0],
        ],
        index=_index(),
        columns=columns,
    )

    result = _extract_universe_frames(frame, ["AAPL", "MSFT"])

    assert set(result) == {"AAPL", "MSFT"}
    assert result["AAPL"]["close"].iloc[-1] == 102.0
    assert result["MSFT"]["close"].iloc[-1] == 202.0


def test_extract_universe_frames_with_price_first_columns():
    columns = pd.MultiIndex.from_tuples(
        [
            ("Close", "BARC.L"),
            ("Volume", "BARC.L"),
            ("Close", "SHEL.L"),
            ("Volume", "SHEL.L"),
        ]
    )
    frame = pd.DataFrame(
        [
            [100.0, 10.0, 200.0, 20.0],
            [101.0, 11.0, 201.0, 21.0],
            [102.0, 12.0, 202.0, 22.0],
        ],
        index=_index(),
        columns=columns,
    )

    result = _extract_universe_frames(frame, ["BARC.L", "SHEL.L"])

    assert set(result) == {"BARC.L", "SHEL.L"}
    assert result["BARC.L"]["close"].iloc[-1] == 102.0
    assert result["SHEL.L"]["close"].iloc[-1] == 202.0
