from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache

import yfinance as yf


@dataclass(frozen=True)
class SymbolMatch:
    symbol: str
    name: str
    exchange: str
    quote_type: str

    def to_dict(self) -> dict:
        return asdict(self)


@lru_cache(maxsize=256)
def _cached_search(query: str) -> tuple[SymbolMatch, ...]:
    search = yf.Search(query, max_results=20)
    quotes = getattr(search, "quotes", []) or []

    matches: list[SymbolMatch] = []
    seen: set[str] = set()

    for item in quotes:
        symbol = str(item.get("symbol", "")).upper().strip()
        quote_type = str(item.get("quoteType") or item.get("typeDisp") or "").strip()
        if not symbol.endswith(".L"):
            continue
        if quote_type and quote_type.upper() not in {"EQUITY", "STOCK"}:
            continue
        if symbol in seen:
            continue

        name = (
            item.get("longname")
            or item.get("shortname")
            or item.get("name")
            or symbol
        )
        exchange = (
            item.get("exchDisp")
            or item.get("exchange")
            or "London Stock Exchange"
        )

        matches.append(
            SymbolMatch(
                symbol=symbol,
                name=str(name).strip(),
                exchange=str(exchange).strip(),
                quote_type=quote_type or "EQUITY",
            )
        )
        seen.add(symbol)

    return tuple(matches)


def search_lse_symbols(query: str, limit: int = 8) -> list[SymbolMatch]:
    normalized = " ".join(query.strip().split())
    if len(normalized) < 2:
        return []

    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")

    return list(_cached_search(normalized.casefold())[:limit])
