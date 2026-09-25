# Architecture

## MVP

1. Market data is ingested for a small liquid LSE universe.
2. Raw data is stored in Azure Data Lake Storage Gen2.
3. Feature engineering produces technical and contextual features.
4. Azure ML or a containerized training job trains and registers models.
5. The API serves prediction outputs.
6. Paper-trading logic evaluates signals after costs.
7. Application Insights and Azure Monitor provide observability.

## Authentication

User authentication uses Microsoft Entra ID with OAuth2/OIDC.

Protected API requests carry a short-lived JWT access token. The API validates:

- signature
- issuer
- audience
- expiry
- roles/scopes

Azure-hosted workloads should use Managed Identity rather than embedded credentials.

Service secrets such as market-data or broker API keys belong in Azure Key Vault. They must never be exposed to the frontend or committed to Git.

## Data roadmap

MVP data can use delayed or free sources for research. Production use should migrate to properly licensed LSE, RNS, order-book, and news feeds.

## Trading roadmap

The repository starts in paper-trading mode. Live execution should only be added after robust walk-forward testing, transaction-cost modeling, slippage analysis, monitoring, and operational controls.
