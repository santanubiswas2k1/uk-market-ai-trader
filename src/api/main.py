import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.ingest.market_data import load_live_quote
from src.markets import MARKETS
from src.security.auth import validate_bearer_token
from src.services.prediction import predict_symbol
from src.services.symbols import search_symbols

app = FastAPI(title="Global Market AI Trader", version="0.6.0")

frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip()
if frontend_origin:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

AuthClaims = Annotated[dict, Depends(validate_bearer_token)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "paper-trading"}


@app.get("/markets")
def markets(claims: AuthClaims) -> dict:
    return {
        "markets": [
            {
                "key": key,
                "label": config.label,
                "default_symbol": config.default_symbol,
            }
            for key, config in MARKETS.items()
        ]
    }


@app.get("/me")
def me(claims: AuthClaims) -> dict:
    return {
        "subject": claims.get("sub"),
        "name": claims.get("name"),
        "preferred_username": claims.get("preferred_username"),
        "roles": claims.get("roles", []),
        "scopes": claims.get("scp", ""),
    }


@app.get("/symbols/search")
def symbol_search(q: str, claims: AuthClaims, market: str = "uk", limit: int = 8) -> dict:
    """Search equities by company name or ticker within the selected market."""
    try:
        matches = search_symbols(q, market=market, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Symbol lookup is temporarily unavailable",
        ) from exc

    return {
        "query": q,
        "market": market,
        "results": [match.to_dict() for match in matches],
    }


@app.get("/quote/{symbol}")
def quote(symbol: str, claims: AuthClaims, market: str = "uk") -> dict:
    """Return a provider quote snapshot for the selected symbol."""
    try:
        return load_live_quote(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Live quote is temporarily unavailable",
        ) from exc


@app.get("/predict/{symbol}")
def predict(symbol: str, claims: AuthClaims, market: str = "uk") -> dict:
    """Protected multi-market research prediction endpoint."""
    try:
        result = predict_symbol(symbol, market=market)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.to_dict()
