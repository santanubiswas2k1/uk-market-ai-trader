from __future__ import annotations

import argparse
import json

from src.markets import MARKETS
from src.services.prediction import predict_symbol


def main() -> None:
    parser = argparse.ArgumentParser(description="Global Market AI Trader research prediction")
    parser.add_argument("symbol", help="Market ticker, for example BARC.L, AAPL or 7203.T")
    parser.add_argument(
        "--market",
        default="uk",
        choices=tuple(MARKETS),
        help="Market configuration to use",
    )
    parser.add_argument(
        "--period",
        default="5y",
        help="History period accepted by the MVP data source",
    )
    args = parser.parse_args()

    prediction = predict_symbol(args.symbol, market=args.market, period=args.period)
    print(json.dumps(prediction.to_dict(), indent=2))


if __name__ == "__main__":
    main()
