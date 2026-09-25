# Five-model ensemble

The prediction service now combines five classification models:

- Logistic Regression
- Random Forest
- XGBoost
- LightGBM
- CatBoost

## Ensemble method

Version 1 uses equal weights:

```text
Logistic Regression  20%
Random Forest        20%
XGBoost              20%
LightGBM             20%
CatBoost             20%
                     ----
Combined             100%
```

The combined next-day probability is the weighted mean of the five individual
`predict_proba` outputs.

## Validation

Every model is evaluated on the same expanding-window walk-forward periods.
The API reports, for each model:

- probability up
- walk-forward accuracy
- Brier score
- ensemble weight

The ensemble itself also receives walk-forward accuracy and Brier metrics.

For the personal-use deployment, each walk-forward fold covers 40 trading rows.
This substantially reduces repeated training compared with retraining every 20
rows while keeping the evaluation chronological.

## Model caching

The service uses the existing Azure Storage account as a private model cache.

```text
models/
  BARC.L/
    latest.joblib
  LLOY.L/
    latest.joblib
  ...
```

The package contains the five trained estimators, ensemble weights, feature
schema, training-data signature and walk-forward metrics.

On a prediction request:

1. current market and context data are loaded
2. the latest training-data signature is calculated
3. a matching package is loaded from Azure Blob Storage when available
4. otherwise the ensemble is trained and evaluated
5. the new package is stored in Blob Storage
6. the latest feature row is scored by all five models

This gives a low-cost lazy refresh model for personal use: the first request
after new labelled market data may retrain, while later requests reuse the
saved models.

## Azure security

The Container App accesses model storage with its user-assigned Managed
Identity. No storage key is placed in application configuration.

The identity receives the Storage Blob Data Contributor role only on the model
storage account.

## Resource controls

The models are deliberately configured conservatively:

- single-threaded XGBoost
- single-threaded Random Forest
- single-threaded LightGBM
- single-threaded CatBoost
- modest tree/iteration counts
- Container Apps scale-to-zero remains enabled

The current Container App remains at 0.5 CPU / 1 GiB initially. Increase memory
only if actual runtime telemetry shows that the ensemble needs it.
