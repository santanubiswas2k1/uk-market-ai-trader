import azure.functions as func
from shared import handle_quote


def main(req: func.HttpRequest) -> func.HttpResponse:
    return handle_quote(req)
