# UK Market AI Trader

Azure-first research platform for UK equity market prediction and paper trading.

## Current MVP

- LSE/FTSE research universe
- Daily UK equity market-data ingestion
- FTSE 100 context features
- GBP/USD context features
- Technical feature engineering
- Normalized RNS event feature pipeline
- Generic UK macro-series normalization for Bank Rate/CPI-style data
- XGBoost baseline classifier
- Expanding-window walk-forward evaluation
- Transaction-cost-aware paper backtest
- FastAPI service
- Microsoft Entra ID JWT validation
- Azure Key Vault integration via DefaultAzureCredential
- Azure Bicep starter infrastructure
- GitHub Actions CI

## Model inputs

The default runnable predictor currently uses:

- individual LSE share price/volume
- 1-day and 5-day share returns
- rolling volatility and moving-average gap
- volume z-score
- FTSE 100 1-day and 5-day returns
- GBP/USD 1-day and 5-day returns
- share return relative to the FTSE 100

The repository also includes normalized feature adapters for **RNS announcements** and **UK macro series**. These are intentionally data-provider-neutral: production use should ingest data from an appropriately licensed/official source and pass it into the normalization layer rather than scrape websites.

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
- `GET /predict/{symbol}` is protected and returns the next-day research probability.

Example symbols: `BARC.L`, `LLOY.L`, `SHEL.L`, `AZN.L`.

## Prediction interpretation

The output contains:

- `probability_up`
- `probability_down`
- `UP / NEUTRAL / DOWN` research signal
- walk-forward accuracy
- walk-forward Brier score
- number of walk-forward folds
- model feature count

The walk-forward test repeatedly trains only on historical observations occurring before each test window. This is substantially more realistic than randomly shuffling financial time-series data.

The returned `close_price` is the source quotation value. Many London-listed equities are quoted in **GBp (pence)** rather than GBP.

## Azure serverless deployment

The production target is Azure Container Apps (Consumption) with scale-to-zero, ACR, Managed Identity and Key Vault. Deployment uses GitHub Actions with Azure OIDC, so no long-lived Azure client secret is stored in GitHub.

See [docs/azure-serverless.md](docs/azure-serverless.md) for the one-time Azure/Entra setup and deployment flow.

## Architecture

See [docs/architecture.md](docs/architecture.md) and [docs/roadmap.md](docs/roadmap.md).

## Security

Do not commit API keys, broker credentials, database passwords, or other secrets. Azure-hosted workloads should use Managed Identity and Azure Key Vault.

## Important

This repository is for research and paper trading. The current free/delayed price source is suitable for prototyping, not necessarily production or live trading. Model probabilities are not guaranteed to be calibrated and are not financial advice.

Before live use, validate data licensing, spread/slippage, transaction costs, corporate actions, survivorship bias, look-ahead bias, release-time alignment for macro/RNS data, probability calibration, walk-forward stability, and operational controls.
