# UK Market AI Trader

Azure-first research platform for UK equity market prediction and paper trading.

## Current MVP

- LSE/FTSE research universe
- Daily market-data ingestion
- Technical feature engineering
- XGBoost baseline classifier
- Chronological holdout evaluation
- Transaction-cost-aware paper backtest
- FastAPI service
- Microsoft Entra ID JWT validation
- Azure Key Vault integration via DefaultAzureCredential
- Azure Bicep starter infrastructure
- GitHub Actions CI

## Architecture

Market/news feeds -> Azure ingestion/storage -> feature pipeline -> model training -> prediction API -> paper trading.

See [docs/architecture.md](docs/architecture.md) and [docs/roadmap.md](docs/roadmap.md).

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

Run a research prediction:

```bash
uk-market-predict BARC.L
# or
python -m src.cli BARC.L
```

Run the API:

```bash
uvicorn src.api.main:app --reload
```

- `GET /health` is public.
- `GET /me` validates a Microsoft Entra ID bearer token.
- `GET /predict/{symbol}` is protected and returns the research model's next-day direction probability.

Example symbols: `BARC.L`, `LLOY.L`, `SHEL.L`, `AZN.L`.

## Prediction interpretation

The MVP returns `probability_up`, `probability_down`, a simple `UP / NEUTRAL / DOWN` research signal, and chronological holdout metrics.

The returned `close_price` is the source quotation value. Many London-listed equities are quoted in **GBp (pence)** rather than GBP, so consumers should not assume the numeric price is pounds without checking the instrument's quote currency.

## Security

Do not commit API keys, broker credentials, database passwords, or other secrets. Azure-hosted workloads should use Managed Identity and Azure Key Vault.

## Important

This repository is for research and paper trading. The current free/delayed source is suitable for prototyping, not necessarily production or live trading. Model probabilities are not guaranteed to be calibrated and are not financial advice.

Before live use, validate market-data licensing, slippage, spread, transaction costs, survivorship bias, look-ahead bias, corporate actions, probability calibration, walk-forward performance, and operational controls.
