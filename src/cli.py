from __future__ import annotations

import argparse
import json

from src.services.prediction import predict_symbol


def main() -> None:
    parser = argparse.ArgumentParser(description="UK Market AI Trader research prediction")
    parser.add_argument("symbol", help="LSE ticker, for example BARC.L")
    parser.add_argument("--period", default="5y", help="History period accepted by the MVP data source")
    args = parser.parse_args()

    prediction = predict_symbol(args.symbol, period=args.period)
    print(json.dumps(prediction.to_dict(), indent=2))


if __name__ == "__main__":
    main()
