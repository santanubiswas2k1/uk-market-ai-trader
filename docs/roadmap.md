# Roadmap

## Phase 1 — complete
- Daily LSE data ingestion
- Technical feature engineering
- XGBoost baseline
- FastAPI service
- Entra ID token validation
- Azure Key Vault integration
- GitHub Actions CI

## Phase 2 — in progress
- FTSE 100 market context
- GBP/USD context
- Expanding-window walk-forward validation
- RNS event normalization
- UK macro-series normalization

## Phase 2 next
- Connect an appropriately licensed RNS feed
- Connect official/approved Bank of England and ONS release data
- Add sector-relative features
- Add probability calibration
- Persist datasets/models to ADLS/Azure ML
- Produce walk-forward equity curves and drawdown statistics

## Phase 3
- Event Hubs streaming ingestion
- Licensed real-time LSE/order-book feed
- Intraday features
- Paper broker integration
- Dashboard and alerting

## Phase 4
- Optional live execution only after extensive validation and controls
