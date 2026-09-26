import azure.functions as func
from shared_code.market_feed import handle_quote


def main(req: func.HttpRequest) -> func.HttpResponse:
    return handle_quote(req)
