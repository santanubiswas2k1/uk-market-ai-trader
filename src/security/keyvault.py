from __future__ import annotations

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from src.config import SETTINGS


def get_secret(name: str) -> str:
    if not SETTINGS.key_vault_url:
        raise RuntimeError("KEY_VAULT_URL is not configured")

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=SETTINGS.key_vault_url, credential=credential)
    return client.get_secret(name).value
