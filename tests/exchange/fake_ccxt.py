"""Cliente ccxt falso: mismas firmas que `CcxtClient`, sin red."""

from __future__ import annotations

from typing import Any


def binance_market(
    base: str,
    quote: str = "USDT",
    *,
    tick: str = "0.01000000",
    step: str = "0.00001000",
    min_qty: str = "0.00001000",
    max_qty: str = "9000.00000000",
    min_notional: str = "5.00000000",
    status: str = "TRADING",
    spot: bool = True,
    with_filters: bool = True,
    order_types: tuple[str, ...] = ("LIMIT", "MARKET", "STOP_LOSS", "STOP_LOSS_LIMIT"),
) -> dict[str, Any]:
    """Mercado con la forma unificada de ccxt para Binance Spot (incluye `info.filters`)."""
    filters: list[dict[str, Any]] = []
    if with_filters:
        filters = [
            {
                "filterType": "PRICE_FILTER",
                "minPrice": "0.01000000",
                "maxPrice": "0",
                "tickSize": tick,
            },
            {"filterType": "LOT_SIZE", "minQty": min_qty, "maxQty": max_qty, "stepSize": step},
            {"filterType": "NOTIONAL", "minNotional": min_notional, "applyMinToMarket": True},
        ]
    return {
        "id": f"{base}{quote}",
        "symbol": f"{base}/{quote}",
        "base": base,
        "quote": quote,
        "spot": spot,
        "active": status == "TRADING",
        "precision": {"price": float(tick), "amount": float(step)},
        "limits": {
            "amount": {"min": float(min_qty), "max": float(max_qty)},
            "cost": {"min": float(min_notional), "max": None},
        },
        "info": {
            "symbol": f"{base}{quote}",
            "status": status,
            "orderTypes": list(order_types),
            "filters": filters,
        },
    }


def kline_row(open_time: int, tf_ms: int, price: float, volume: float) -> list[Any]:
    """Una kline cruda de Binance: montos como string de 8 decimales, closeTime = open + tf − 1."""
    return [
        open_time,
        f"{price:.8f}",
        f"{price + 5:.8f}",
        f"{price - 5:.8f}",
        f"{price + 1:.8f}",
        f"{volume:.8f}",
        open_time + tf_ms - 1,
        f"{volume * price:.8f}",
        100,
        f"{volume / 2:.8f}",
        f"{volume * price / 2:.8f}",
        "0",
    ]


def ohlcv_rows(start_ms: int, tf_ms: int, n: int, base_price: float = 100.0) -> list[list[Any]]:
    """`n` klines consecutivas y determinísticas (formato crudo de Binance)."""
    return [kline_row(start_ms + i * tf_ms, tf_ms, base_price + i, 1000.0 + i) for i in range(n)]


EXCHANGE_INFO: dict[str, Any] = {
    "rateLimits": [
        {"rateLimitType": "REQUEST_WEIGHT", "interval": "MINUTE", "intervalNum": 1, "limit": 6000},
        {"rateLimitType": "ORDERS", "interval": "SECOND", "intervalNum": 10, "limit": 100},
        {"rateLimitType": "ORDERS", "interval": "DAY", "intervalNum": 1, "limit": 200000},
        {"rateLimitType": "RAW_REQUESTS", "interval": "MINUTE", "intervalNum": 5, "limit": 61000},
    ]
}


class FakeCcxt:
    """Devuelve datos preparados y permite inyectar fallas en orden."""

    def __init__(
        self,
        markets: dict[str, dict[str, Any]] | None = None,
        candles: dict[tuple[str, str], list[list[Any]]] | None = None,
        server_time_ms: int = 1_700_000_000_000,
        failures: list[Exception] | None = None,
        exchange_info: dict[str, Any] | None = None,
    ) -> None:
        self.markets = markets if markets is not None else {"BTC/USDT": binance_market("BTC")}
        self.candles = candles or {}
        self.server_time_ms = server_time_ms
        self.failures = list(failures or [])
        self.exchange_info = exchange_info or EXCHANGE_INFO
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        # Falla permanente en klines a partir de este startTime (simula caída a mitad de descarga).
        self.fail_klines_from: int | None = None
        self.klines_failure: Exception | None = None
        self.last_response_headers: dict[str, str] = {}
        self.last_prices: dict[str, str] = {}  # símbolo Binance -> precio como string

    def _maybe_fail(self) -> None:
        if self.failures:
            raise self.failures.pop(0)

    def count(self, name: str) -> int:
        return sum(1 for call in self.calls if call[0] == name)

    def load_markets(self, reload: bool = False) -> dict[str, Any]:
        self.calls.append(("load_markets", (reload,)))
        self._maybe_fail()
        return dict(self.markets)

    def fetch_time(self) -> int:
        self.calls.append(("fetch_time", ()))
        self._maybe_fail()
        return self.server_time_ms

    def public_get_klines(self, params: dict[str, Any] | None = None) -> list[list[Any]]:
        params = dict(params or {})
        symbol = str(params["symbol"])
        interval = str(params["interval"])
        since = params.get("startTime")
        limit = params.get("limit")
        self.calls.append(("klines", (symbol, interval, since, limit)))
        self._maybe_fail()
        if (
            self.fail_klines_from is not None
            and since is not None
            and int(since) >= self.fail_klines_from
        ):
            assert self.klines_failure is not None
            raise self.klines_failure
        ccxt_symbol = f"{symbol[:-4]}/{symbol[-4:]}"  # BTCUSDT → BTC/USDT (quote USDT)
        rows = self.candles.get((ccxt_symbol, interval), [])
        if since is not None:
            rows = [r for r in rows if r[0] >= int(since)]
        if limit is not None:
            rows = rows[: int(limit)]
        return [list(r) for r in rows]

    def public_get_exchangeinfo(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append(("public_get_exchangeinfo", ()))
        self._maybe_fail()
        return dict(self.exchange_info)

    def public_get_ticker_price(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        symbol = str((params or {}).get("symbol"))
        self.calls.append(("ticker_price", (symbol,)))
        self._maybe_fail()
        return {"symbol": symbol, "price": self.last_prices.get(symbol, "0")}
