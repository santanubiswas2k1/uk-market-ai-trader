import json

import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(
            {
                "status": "ok",
                "service": "market-feed",
                "provider": "Twelve Data",
            }
        ),
        status_code=200,
        mimetype="application/json",
        headers={"Cache-Control": "no-store"},
    )
