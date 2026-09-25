from fastapi import Depends, FastAPI

from src.security.auth import validate_bearer_token

app = FastAPI(title="UK Market AI Trader", version="0.1.0")


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
