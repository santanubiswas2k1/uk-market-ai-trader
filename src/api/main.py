from fastapi import Depends, FastAPI, HTTPException

from src.security.auth import validate_bearer_token
from src.services.prediction import predict_symbol

app = FastAPI(title="UK Market AI Trader", version="0.2.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "paper-trading"}


@app.get("/me")
def me(claims: dict = Depends(validate_bearer_token)) -> dict:
    return {
        "subject": claims.get("sub"),
        "name": claims.get("name"),
        "preferred_username": claims.get("preferred_username"),
        "roles": claims.get("roles", []),
        "scopes": claims.get("scp", ""),
    }


@app.get("/predict/{symbol}")
def predict(symbol: str, claims: dict = Depends(validate_bearer_token)) -> dict:
    """Protected research prediction endpoint."""
    try:
        result = predict_symbol(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.to_dict()
