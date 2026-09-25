from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache

import yfinance as yf

from src.markets import get_market


@dataclass(frozen=True)
class SymbolMatch:
    symbol: str
    name: str
    exchange: str
    quote_type: str

    def to_dict(self) -> dict:
        return asdict(self)


def _is_market_match(symbol: str, exchange: str, market: str) -> bool:
    config = get_market(market)
    normalized_symbol = symbol.upper()
    normalized_exchange = exchange.casefold()

    suffix_match = bool(config.symbol_suffixes) and normalized_symbol.endswith(
        config.symbol_suffixes
    )
    exchange_match = any(
        candidate.casefold() in normalized_exchange for candidate in config.exchange_names
    )

    if market == "us":
        return "." not in normalized_symbol and exchange_match

    return suffix_match or exchange_match


@lru_cache(maxsize=512)
def _cached_search(query: str, market: str) -> tuple[SymbolMatch, ...]:
    search = yf.Search(query, max_results=30)
    quotes = getattr(search, "quotes", []) or []

    matches: list[SymbolMatch] = []
    seen: set[str] = set()

    for item in quotes:
        symbol = str(item.get("symbol", "")).upper().strip()
        quote_type = str(item.get("quoteType") or item.get("typeDisp") or "").strip()
        exchange = str(
            item.get("exchDisp")
            or item.get("exchange")
            or ""
        ).strip()

        if quote_type and quote_type.upper() not in {"EQUITY", "STOCK"}:
            continue
        if not symbol or symbol in seen:
            continue
        if not _is_market_match(symbol, exchange, market):
            continue

        name = (
            item.get("longname")
            or item.get("shortname")
            or item.get("name")
            or symbol
        )

        matches.append(
            SymbolMatch(
                symbol=symbol,
                name=str(name).strip(),
                exchange=exchange or get_market(market).label,
                quote_type=quote_type or "EQUITY",
            )
        )
        seen.add(symbol)

    return tuple(matches)


def search_symbols(query: str, market: str = "uk", limit: int = 8) -> list[SymbolMatch]:
    normalized = " ".join(query.strip().split())
    get_market(market)

    if len(normalized) < 2:
        return []

    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")

    return list(_cached_search(normalized.casefold(), market.lower())[:limit])
