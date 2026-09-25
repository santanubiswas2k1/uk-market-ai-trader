from __future__ import annotations

import io
import os
from typing import Any

import joblib
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError, ResourceExistsError, ResourceNotFoundError

CONTAINER_NAME = "models"


def _service_client() -> BlobServiceClient | None:
    account_url = os.getenv("MODEL_STORAGE_ACCOUNT_URL", "").strip()
    if not account_url:
        return None

    return BlobServiceClient(
        account_url=account_url,
        credential=DefaultAzureCredential(),
    )


def load_model_package(symbol: str) -> dict[str, Any] | None:
    service = _service_client()
    if service is None:
        return None

    blob = service.get_blob_client(
        container=CONTAINER_NAME,
        blob=f"{symbol.upper()}/latest.joblib",
    )
    try:
        payload = blob.download_blob().readall()
    except (ResourceNotFoundError, AzureError):
        return None

    return joblib.load(io.BytesIO(payload))


def save_model_package(symbol: str, package: dict[str, Any]) -> bool:
    service = _service_client()
    if service is None:
        return False

    container = service.get_container_client(CONTAINER_NAME)
    try:
        container.create_container()
    except ResourceExistsError:
        pass
    except AzureError:
        return False

    buffer = io.BytesIO()
    joblib.dump(package, buffer, compress=3)
    buffer.seek(0)

    try:
        container.upload_blob(
            name=f"{symbol.upper()}/latest.joblib",
            data=buffer,
            overwrite=True,
        )
    except AzureError:
        return False

    return True
