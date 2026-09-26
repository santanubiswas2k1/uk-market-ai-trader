import json
import os

import azure.functions as func


def _error_response(detail: str, status_code: int = 500) -> func.HttpResponse:
    origin = os.getenv("FRONTEND_ORIGIN", "").rstrip("/")
    headers = {
        "Access-Control-Allow-Origin": origin or "*",
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Cache-Control": "no-store",
    }
    return func.HttpResponse(
        json.dumps({"detail": detail}),
        status_code=status_code,
        mimetype="application/json",
        headers=headers,
    )


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        from shared_code.market_feed import handle_quote

        return handle_quote(req)
    except Exception as exc:  # noqa: BLE001
        return _error_response(
            f"Market feed runtime error: {type(exc).__name__}",
            status_code=500,
        )
