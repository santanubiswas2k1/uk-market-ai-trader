import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.security.auth import validate_bearer_token
from src.services.prediction import predict_symbol

app = FastAPI(title="UK Market AI Trader", version="0.3.0")

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


@app.get("/me")
def me(claims: AuthClaims) -> dict:
    return {
        "subject": claims.get("sub"),
        "name": claims.get("name"),
        "preferred_username": claims.get("preferred_username"),
        "roles": claims.get("roles", []),
        "scopes": claims.get("scp", ""),
    }


@app.get("/predict/{symbol}")
def predict(symbol: str, claims: AuthClaims) -> dict:
    """Protected research prediction endpoint."""
    try:
        result = predict_symbol(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.to_dict()
