from __future__ import annotations

from functools import lru_cache

import httpx
import jwt
from fastapi import Header, HTTPException, status

from src.config import SETTINGS

REQUIRED_SCOPE = "access_as_user"


@lru_cache(maxsize=1)
def _openid_config() -> dict:
    if not SETTINGS.azure_tenant_id:
        raise RuntimeError("AZURE_TENANT_ID is not configured")
    url = (
        f"https://login.microsoftonline.com/{SETTINGS.azure_tenant_id}"
        "/v2.0/.well-known/openid-configuration"
    )
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


@lru_cache(maxsize=1)
def _jwks() -> dict:
    config = _openid_config()
    response = httpx.get(config["jwks_uri"], timeout=10)
    response.raise_for_status()
    return response.json()


def _valid_audiences() -> list[str]:
    audience = (SETTINGS.api_audience or "").strip()
    if not audience:
        return []

    audiences = {audience}
    if audience.startswith("api://"):
        audiences.add(audience.removeprefix("api://"))

    return sorted(audiences)


def _valid_issuers() -> set[str]:
    tenant_id = (SETTINGS.azure_tenant_id or "").strip()
    if not tenant_id:
        return set()

    return {
        f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        f"https://sts.windows.net/{tenant_id}/",
    }


def _validate_claims(claims: dict) -> None:
    tenant_id = (SETTINGS.azure_tenant_id or "").strip()
    if tenant_id and claims.get("tid") != tenant_id:
        raise ValueError("Token tenant does not match configured tenant")

    if claims.get("iss") not in _valid_issuers():
        raise ValueError("Token issuer is not valid for configured tenant")

    scopes = set(str(claims.get("scp", "")).split())
    if REQUIRED_SCOPE not in scopes:
        raise ValueError(f"Required delegated scope '{REQUIRED_SCOPE}' is missing")


def validate_bearer_token(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = authorization.removeprefix("Bearer ").strip()

    try:
        header = jwt.get_unverified_header(token)
        jwk = next(key for key in _jwks()["keys"] if key["kid"] == header["kid"])
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)

        audiences = _valid_audiences()
        options = {"require": ["exp", "iat", "iss", "aud", "tid"]}
        decode_kwargs = {
            "algorithms": ["RS256"],
            "options": options,
        }

        if audiences:
            decode_kwargs["audience"] = audiences
        else:
            options["verify_aud"] = False

        claims = jwt.decode(token, public_key, **decode_kwargs)
        _validate_claims(claims)
        return claims
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc
