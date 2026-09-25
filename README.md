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
uvicorn src.api.main:app --reload
```

The API health endpoint is available at `/health`. The `/me` endpoint is protected by Entra ID bearer-token validation.

## Security

Do not commit API keys, broker credentials, database passwords, or other secrets. Azure-hosted workloads should use Managed Identity and Azure Key Vault.

## Important

This repository is for research and paper trading. Free/delayed data sources are suitable for prototyping, not necessarily for production or live trading. Before live use, validate licensing, slippage, spread, transaction costs, survivorship bias, look-ahead bias, corporate actions, calibration, and operational controls.
