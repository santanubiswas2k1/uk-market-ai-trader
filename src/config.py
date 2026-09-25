import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    prediction_horizon_days: int = int(os.getenv("PREDICTION_HORIZON_DAYS", "1"))
    min_training_rows: int = int(os.getenv("MIN_TRAINING_ROWS", "250"))
    initial_cash_gbp: float = float(os.getenv("INITIAL_CASH_GBP", "100000"))
    transaction_cost_bps: float = float(os.getenv("TRANSACTION_COST_BPS", "10"))
    azure_tenant_id: str | None = os.getenv("AZURE_TENANT_ID")
    azure_client_id: str | None = os.getenv("AZURE_CLIENT_ID")
    api_audience: str | None = os.getenv("API_AUDIENCE")
    key_vault_url: str | None = os.getenv("KEY_VAULT_URL")


SETTINGS = Settings()
