# Global Market AI Trader

Azure-first research platform for multi-market equity prediction and paper trading.

## Current MVP

- Multi-market research universe: UK, US, India, UAE, Canada, Europe, Hong Kong, Japan and Australia
- Company-name lookup filtered to the selected market
- Daily equity market-data ingestion
- Market-specific broad-index context
- Market-specific FX context
- Technical feature engineering
- Normalized RNS event feature pipeline
- Generic UK macro-series normalization for Bank Rate/CPI-style data
- Five-model direction ensemble: Logistic Regression, Random Forest, XGBoost, LightGBM and CatBoost
- Five-model return ensemble: Ridge, Random Forest, XGBoost, LightGBM and CatBoost
- Expanding-window walk-forward evaluation
- Transaction-cost-aware paper backtest
- FastAPI AI/prediction service
- Separate Azure Function market-feed proxy for Twelve Data quotes
- Microsoft Entra ID JWT validation
- Azure Key Vault integration via DefaultAzureCredential
- Azure Bicep starter infrastructure
- GitHub Actions CI

## Model inputs

The default runnable predictor uses a five-model equal-weight ensemble over:

- individual share price/volume
- 1-day and 5-day share returns
- rolling volatility and moving-average gap
- volume z-score
- selected market index 1-day and 5-day returns
- selected market FX/proxy 1-day and 5-day returns
- share return relative to the selected market index
- sector proxy 1-day and 5-day returns and stock-vs-sector relative return
- VIX, US 10-year yield, oil and gold daily context

The prediction response includes live **news sentiment, recent headlines, sector metadata and upcoming earnings context**. Live company-news sentiment is fused into the final direction probability and expected return with a bounded weight, while nearby earnings widen the expected price range. Historical walk-forward metrics do not yet include this live news overlay; a point-in-time historical news archive is required to backtest and train that layer without leakage.

The repository also includes normalized feature adapters for **RNS announcements** and **macro series**. These are intentionally data-provider-neutral: production use should ingest data from an appropriately licensed/official source and pass it into the normalization layer rather than scrape websites.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

Run a research prediction:

```bash
uk-market-predict BARC.L --market uk
uk-market-predict AAPL --market us
uk-market-predict RELIANCE.NS --market india
```

Run the API:

```bash
uvicorn src.api.main:app --reload
```

- `GET /health` is public.
- `GET /me` validates a Microsoft Entra ID bearer token.
- `GET /symbols/search?q=Apple&market=us` performs protected company lookup.
- `GET /predict/{symbol}?market=us` is protected and returns the next-day research probability.

Example symbols: `BARC.L`, `AAPL`, `RELIANCE.NS`, `RY.TO`, `SAP.DE`, `0700.HK`, `7203.T`, `BHP.AX`.

## Prediction interpretation

The output contains:

- `probability_up` and `probability_down` for the direction ensemble
- `expected_return_1d` from a five-model return regression ensemble
- `expected_close` derived from the latest close and expected return
- `expected_range_low` / `expected_range_high` as an 80% volatility-based next-day range
- individual probability from each of the five models
- per-model walk-forward accuracy and Brier score
- model weights and cache/training source
- `UP / NEUTRAL / DOWN` research signal
- walk-forward accuracy
- walk-forward Brier score
- number of walk-forward folds
- model feature count

The walk-forward test repeatedly trains only on historical observations occurring before each test window. This is substantially more realistic than randomly shuffling financial time-series data.

The returned `close_price` is the source quotation value and therefore uses the quotation convention of the selected exchange. Many London-listed equities, for example, are quoted in **GBp (pence)** rather than GBP.

## Azure serverless deployment

The production target is Azure Container Apps (Consumption) with scale-to-zero, ACR, Managed Identity and Key Vault. Deployment uses GitHub Actions with Azure OIDC, so no long-lived Azure client secret is stored in GitHub.

See [docs/azure-serverless.md](docs/azure-serverless.md) for the one-time Azure/Entra setup and deployment flow.

See [docs/market-feed.md](docs/market-feed.md) for the Twelve Data market-feed proxy and required API-key setup.

## Architecture

See [docs/architecture.md](docs/architecture.md) and [docs/roadmap.md](docs/roadmap.md).

## Security

Do not commit API keys, broker credentials, database passwords, or other secrets. Azure-hosted workloads should use Managed Identity and Azure Key Vault.

## Important

This repository is for research and paper trading. The current free/delayed price source is suitable for prototyping, not necessarily production or live trading. Model probabilities are not guaranteed to be calibrated and are not financial advice.

Before live use, validate data licensing, spread/slippage, transaction costs, corporate actions, survivorship bias, look-ahead bias, release-time alignment for macro/RNS data, probability calibration, walk-forward stability, and operational controls.


## Forward prediction accuracy

Each first daily live forecast is stored in Azure Blob Storage and later
reconciled against the next completed trading-day close. The dashboard reports
direction accuracy, signal accuracy, Brier score, expected-close error, return
error and predicted-range hit rate.

See [docs/prediction-accuracy.md](docs/prediction-accuracy.md) for the ledger
format and metric definitions.
