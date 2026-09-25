# Market feed

The dashboard market-data panel uses a separate Azure Function proxy rather than
the ML Container App.

## Flow

Browser -> Azure Function -> Twelve Data REST quote API

The Function validates the same Microsoft Entra delegated access token used by
the main API. The Twelve Data API key is read from Azure Key Vault and is never
sent to the browser.

## Required secret

Create a GitHub Actions repository secret named:

`TWELVE_DATA_API_KEY`

During the manual Azure deployment workflow the value is written to Key Vault
as:

`twelve-data-api-key`

If the secret is not present, deployment still succeeds, but the market feed
returns a configuration error until the Key Vault secret exists.

## Frontend runtime config

The deployment writes:

- `marketFeedBaseUrl` - Azure Function URL ending in `/api`
- `marketFeedRefreshMs` - default 60000 milliseconds

The live market panel can be paused from the dashboard.

## Provider behavior

The proxy calls Twelve Data `/quote` and normalizes its response into:

- price
- previous close
- absolute and percentage change
- open
- day high and low
- volume
- currency
- exchange
- market timestamp/status fields when supplied

Availability, latency and real-time entitlement depend on the selected Twelve
Data plan and exchange.

## Future streaming upgrade

The frontend API wrapper is deliberately separate from the AI API. A future
WebSocket/streaming provider can replace the REST polling implementation
without changing the prediction service.
