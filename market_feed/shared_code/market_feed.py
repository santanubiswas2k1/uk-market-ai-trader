from __future__ import annotations

import json
import os
from functools import lru_cache
from urllib.parse import urlencode

import azure.functions as func
import httpx
import jwt
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

REQUIRED_SCOPE = "access_as_user"
TWELVE_DATA_BASE_URL = "https://api.twelvedata.com"

SYMBOL_MARKET_MAP = {
    ".L": ("United Kingdom", "LSE"),
    ".NS": ("India", "NSE"),
    ".BO": ("India", "BSE"),
    ".TO": ("Canada", "TSX"),
    ".V": ("Canada", "TSXV"),
    ".HK": ("Hong Kong", "HKEX"),
    ".T": ("Japan", "TSE"),
    ".AX": ("Australia", "ASX"),
    ".DU": ("United Arab Emirates", "DFM"),
    ".AE": ("United Arab Emirates", "ADX"),
    ".DE": ("Germany", None),
    ".PA": ("France", None),
    ".AS": ("Netherlands", None),
    ".MI": ("Italy", None),
    ".MC": ("Spain", None),
    ".BR": ("Belgium", None),
    ".LS": ("Portugal", None),
    ".VI": ("Austria", None),
}


def response_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store",
    }


def json_response(payload: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(payload),
        status_code=status_code,
        mimetype="application/json",
        headers=response_headers(),
    )


@lru_cache(maxsize=1)
def _openid_config() -> dict:
    tenant_id = os.getenv("AZURE_TENANT_ID", "").strip()
    if not tenant_id:
        raise RuntimeError("AZURE_TENANT_ID is not configured")

    url = (
        f"https://login.microsoftonline.com/{tenant_id}"
        "/v2.0/.well-known/openid-configuration"
    )
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


@lru_cache(maxsize=1)
def _jwks() -> dict:
    response = httpx.get(_openid_config()["jwks_uri"], timeout=10)
    response.raise_for_status()
    return response.json()


def _valid_audiences() -> list[str]:
    audience = os.getenv("API_AUDIENCE", "").strip()
    if not audience:
        return []

    audiences = {audience}
    if audience.startswith("api://"):
        audiences.add(audience.removeprefix("api://"))
    return sorted(audiences)


def validate_token(request: func.HttpRequest) -> None:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise ValueError("Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    tenant_id = os.getenv("AZURE_TENANT_ID", "").strip()

    header = jwt.get_unverified_header(token)
    jwk = next(key for key in _jwks()["keys"] if key["kid"] == header["kid"])
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)

    options = {"require": ["exp", "iat", "iss", "aud", "tid"]}
    kwargs = {
        "algorithms": ["RS256"],
        "options": options,
    }
    audiences = _valid_audiences()
    if audiences:
        kwargs["audience"] = audiences
    else:
        options["verify_aud"] = False

    claims = jwt.decode(token, public_key, **kwargs)

    valid_issuers = {
        f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        f"https://sts.windows.net/{tenant_id}/",
    }
    if claims.get("tid") != tenant_id or claims.get("iss") not in valid_issuers:
        raise ValueError("Token tenant or issuer is invalid")

    scopes = set(str(claims.get("scp", "")).split())
    if REQUIRED_SCOPE not in scopes:
        raise ValueError("Required delegated scope is missing")


@lru_cache(maxsize=1)
def _twelve_data_api_key() -> str:
    vault_url = os.getenv("KEY_VAULT_URL", "").strip()
    if not vault_url:
        raise RuntimeError("KEY_VAULT_URL is not configured")

    client_id = os.getenv("AZURE_CLIENT_ID", "").strip() or None
    credential = DefaultAzureCredential(
        managed_identity_client_id=client_id,
    )
    client = SecretClient(vault_url=vault_url, credential=credential)
    secret = client.get_secret("twelve-data-api-key")
    if not secret.value:
        raise RuntimeError("Twelve Data API key secret is empty")
    return secret.value


def _provider_symbol(symbol: str) -> tuple[str, str | None, str | None]:
    normalized = symbol.strip().upper()
    for suffix, (country, exchange) in SYMBOL_MARKET_MAP.items():
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)], country, exchange
    return normalized, None, None


def _number(payload: dict, key: str) -> float | None:
    value = payload.get(key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(payload: dict, key: str) -> int | None:
    value = payload.get(key)
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def handle_quote(request: func.HttpRequest) -> func.HttpResponse:
    if request.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=response_headers())

    try:
        validate_token(request)
    except Exception:  # noqa: BLE001
        return json_response({"detail": "Unauthorized"}, status_code=401)

    symbol = (request.params.get("symbol") or "").strip().upper()
    if not symbol:
        return json_response({"detail": "symbol is required"}, status_code=400)

    provider_symbol, country, exchange = _provider_symbol(symbol)
    params = {
        "symbol": provider_symbol,
        "interval": "1min",
        "dp": "5",
    }
    if country:
        params["country"] = country
    if exchange:
        params["exchange"] = exchange

    params["apikey"] = _twelve_data_api_key()
    url = f"{TWELVE_DATA_BASE_URL}/quote?{urlencode(params)}"

    try:
        response = httpx.get(url, timeout=12)
    except httpx.HTTPError:
        return json_response(
            {"detail": "Unable to connect to the market-data provider"},
            status_code=502,
        )
    except RuntimeError as exc:
        return json_response({"detail": str(exc)}, status_code=503)

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if not response.is_success:
        provider_detail = payload.get("message") if isinstance(payload, dict) else None
        return json_response(
            {
                "detail": provider_detail
                or f"Market-data provider returned HTTP {response.status_code}",
                "provider_code": payload.get("code")
                if isinstance(payload, dict)
                else None,
            },
            status_code=502,
        )

    if payload.get("status") == "error":
        return json_response(
            {
                "detail": payload.get(
                    "message",
                    "Market-data provider returned an error",
                ),
                "provider_code": payload.get("code"),
            },
            status_code=502,
        )

    close = _number(payload, "close")
    previous_close = _number(payload, "previous_close")
    change = _number(payload, "change")
    percent_change = _number(payload, "percent_change")

    if change is None and close is not None and previous_close is not None:
        change = close - previous_close
    if (
        percent_change is None
        and change is not None
        and previous_close not in (None, 0.0)
    ):
        percent_change = change / previous_close * 100.0

    return json_response(
        {
            "symbol": symbol,
            "provider_symbol": payload.get("symbol") or provider_symbol,
            "name": payload.get("name"),
            "price": close,
            "open": _number(payload, "open"),
            "previous_close": previous_close,
            "change": change,
            "change_percent": (
                percent_change / 100.0 if percent_change is not None else None
            ),
            "day_high": _number(payload, "high"),
            "day_low": _number(payload, "low"),
            "volume": _integer(payload, "volume"),
            "currency": payload.get("currency"),
            "exchange": payload.get("exchange"),
            "mic_code": payload.get("mic_code"),
            "last_update": payload.get("datetime"),
            "timestamp": payload.get("timestamp"),
            "is_market_open": payload.get("is_market_open"),
            "is_extended_hours": payload.get("is_extended_hours"),
            "feed_status": "provider_realtime_or_delayed_by_entitlement",
            "feed_source": "Twelve Data",
        }
    )
