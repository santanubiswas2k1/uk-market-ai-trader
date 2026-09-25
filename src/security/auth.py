from __future__ import annotations

from functools import lru_cache

import httpx
import jwt
from fastapi import Header, HTTPException, status

from src.config import SETTINGS


@lru_cache(maxsize=1)
def _openid_config() -> dict:
    if not SETTINGS.azure_tenant_id:
        raise RuntimeError("AZURE_TENANT_ID is not configured")
    url = (
        f"https://login.microsoftonline.com/{SETTINGS.azure_tenant_id}"
        "/v2.0/.well-known/openid-configuration"
    )
    return httpx.get(url, timeout=10).json()


@lru_cache(maxsize=1)
def _jwks() -> dict:
    config = _openid_config()
    return httpx.get(config["jwks_uri"], timeout=10).json()


def validate_bearer_token(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        header = jwt.get_unverified_header(token)
        jwk = next(k for k in _jwks()["keys"] if k["kid"] == header["kid"])
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)

        kwargs = {
            "algorithms": ["RS256"],
            "issuer": _openid_config()["issuer"],
            "options": {"require": ["exp", "iat", "iss"]},
        }
        if SETTINGS.api_audience:
            audiences = [SETTINGS.api_audience]
            if SETTINGS.api_audience.startswith("api://"):
                audiences.append(SETTINGS.api_audience.removeprefix("api://"))
            kwargs["audience"] = audiences
        else:
            kwargs["options"]["verify_aud"] = False

        return jwt.decode(token, public_key, **kwargs)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc
