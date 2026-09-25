# Architecture

## Research data flow

```text
LSE share history ───────────────┐
FTSE 100 context ────────────────┤
GBP/USD context ─────────────────┤
Licensed RNS events (optional) ──┤
UK macro series (optional) ──────┘
                  │
                  v
        Feature engineering
                  │
                  v
       Expanding walk-forward
             evaluation
                  │
                  v
          XGBoost training
                  │
                  v
          Prediction API
                  │
                  v
          Paper-trading layer
```

## Azure target architecture

For production deployment:

1. Azure Functions or Container Apps ingest market/context/event data.
2. Event Hubs can be introduced for streaming feeds.
3. ADLS Gen2 stores immutable raw and curated datasets.
4. Azure ML trains, tracks and registers models.
5. A containerized FastAPI service exposes inference.
6. Azure Key Vault stores third-party service secrets.
7. Managed Identity authenticates Azure workloads.
8. Application Insights/Azure Monitor provide observability.

## Authentication

User authentication uses Microsoft Entra ID with OAuth2/OIDC.

Protected API requests carry short-lived JWT access tokens. The API validates signature, issuer, audience, expiry, and then exposes roles/scopes to application authorization logic.

Azure-hosted workloads should use Managed Identity rather than embedded Azure credentials.

## RNS design

The repository does not scrape regulatory-news web pages. `aggregate_rns_daily` accepts normalized, vendor-supplied events with timestamps and symbols, then generates count, sentiment, and importance features.

This keeps data licensing and transport separate from model feature engineering.

## Macro design

`normalize_macro_series` accepts dated macro observations, such as Bank Rate or CPI. For backtesting, the supplied date should represent when the value became known to the market (release/effective timestamp where appropriate) to avoid look-ahead bias.

## Evaluation

The default predictor uses expanding-window walk-forward evaluation. Every test fold is scored using a model fitted only on earlier rows.

## Trading roadmap

The repository remains paper-trading only. Live execution should be added only after stronger data licensing, calibration, transaction-cost/slippage modelling, monitoring, and operational risk controls.
