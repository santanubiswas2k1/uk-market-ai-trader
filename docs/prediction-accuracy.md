# Forward prediction accuracy

Live forecasts are stored separately from trained model packages in the existing
Azure Blob Storage account.

## Storage

Container:

`predictions`

Blob naming:

`{market}/{symbol}/{forecast-date}.json`

Example:

`us/AAPL/2026-09-25.json`

Only the first forecast for a market, symbol and model as-of date is retained.
Running the same prediction repeatedly on the same day does not create extra
accuracy samples.

## Stored forecast fields

Each record includes:

- market and symbol
- model as-of timestamp
- source close used for the forecast
- final and base direction probabilities
- UP / DOWN / NEUTRAL signal
- expected next-day return
- expected next close
- expected price range
- news sentiment, news count and sentiment weight
- model source and feature count

After evaluation it also includes:

- next completed trading-day close
- actual next-day return
- actual direction
- direction correctness
- signal correctness
- Brier score
- absolute expected-close error
- expected-close percentage error
- absolute return error
- whether the actual close fell inside the expected range
- evaluation timestamp

## Reconciliation

The protected `GET /performance` endpoint checks pending forecasts against
daily market history. A forecast is evaluated only when the first subsequent
daily bar is from a date earlier than the current UTC date. This prevents an
in-progress current-day bar from being treated as the final close.

Reconciliation is lazy: it runs when performance is requested. It does not yet
require a scheduled Azure job.

## Metrics

The dashboard reports:

- **Direction accuracy**: whether probability_up >= 0.5 matched the actual
  next-day direction.
- **Signal accuracy**: accuracy of explicit UP/DOWN signals. NEUTRAL forecasts
  are excluded from this metric.
- **Brier score**: mean squared probability error for the UP outcome.
- **Expected-close MAE**: mean absolute difference between predicted and actual
  next close, in source quote units.
- **Close MAPE**: expected-close error as a fraction of actual close.
- **Return MAE**: mean absolute error of predicted next-day return.
- **Range hit rate**: share of evaluated closes that landed inside the predicted
  range.

These are forward-test metrics and are intentionally shown separately from the
historical walk-forward metrics used during model evaluation.
