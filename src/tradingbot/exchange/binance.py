"""Adapter de Binance Spot sobre ccxt.

Único punto del proyecto que habla con ccxt. Traduce:

- mercados de Binance → `MarketInfo` con `tick_size`/`step_size`/`min_qty`/`min_notional` en
  `Decimal`, leídos como **string** desde los filtros crudos (`PRICE_FILTER`, `LOT_SIZE`,
  `NOTIONAL`) para no pasar por float;
- klines crudas (`GET /api/v3/klines`, strings de 8 decimales) → `Candle` con `to_decimal(str)`.
  No se usa `fetch_ohlcv` unificado porque ccxt convierte a float y un volumen de 17 dígitos
  significativos perdería el último. Se pagina de a 1000 deduplicando por `open_time`;
- errores de ccxt → excepciones del dominio (`domain/errors.py`). Solo se reintenta lo transitorio
  (`ccxt.OperationFailed`: timeouts, mantenimiento, 429, respuestas rotas) con backoff exponencial;
  nunca `InvalidOrder`, `InsufficientFunds`, `AuthenticationError` ni un 418 (IP baneada: seguir
  pegando alarga el ban).

El cliente ccxt es síncrono e inyectable (`CcxtClient`): los tests usan un cliente falso. El
reloj del exchange se expone con offset cacheado (`now_ms`), refrescado cada hora, porque el
cierre de vela lo define Binance y no el reloj local (CLAUDE.md, regla 8).
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable, Iterator, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from importlib import resources
from pathlib import Path
from typing import Any, Protocol, Self

import ccxt
from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbot.domain.candle import Candle
from tradingbot.domain.errors import (
    AuthError,
    ExchangeError,
    ExchangeUnavailable,
    InsufficientFunds,
    InvalidOrder,
    RateLimited,
)
from tradingbot.domain.money import quantize_price, quantize_qty, to_decimal
from tradingbot.domain.pair import ALLOWED_QUOTES, Pair
from tradingbot.domain.timeframe import Timeframe
from tradingbot.persistence.files import atomic_write_text

log = logging.getLogger(__name__)

EXCHANGE_ID = "binance"
OHLCV_PAGE_LIMIT = 1000  # máximo de Binance Spot por request de klines
TIME_OFFSET_REFRESH_MS = 3_600_000  # una hora
SNAPSHOT_FILENAME = "markets_snapshot.json"
SNAPSHOT_VERSION = 1
_QUERY_RE = re.compile(r"\?[^\s'\"]*")


class MarketInfo(BaseModel):
    """Filtros de un símbolo de Binance Spot que el bot necesita para operar.

    En Binance los "precision" de ccxt son tamaños de paso, no cantidad de decimales:
    `tick_size` (PRICE_FILTER.tickSize), `step_size` (LOT_SIZE.stepSize). `min_notional`
    (NOTIONAL.minNotional, hoy 5 USDT) aplica a entradas y salidas.
    """

    model_config = ConfigDict(frozen=True)

    pair: Pair
    tick_size: Decimal = Field(gt=0)
    step_size: Decimal = Field(gt=0)
    min_qty: Decimal = Field(ge=0)
    max_qty: Decimal | None = Field(default=None, gt=0)
    min_notional: Decimal = Field(ge=0)
    active: bool = True
    order_types: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.max_qty is not None and self.max_qty < self.min_qty:
            msg = f"max_qty {self.max_qty} < min_qty {self.min_qty}"
            raise ValueError(msg)
        return self

    def quantize_price(self, price: Decimal) -> Decimal:
        return quantize_price(price, self.tick_size)

    def quantize_qty(self, qty: Decimal) -> Decimal:
        return quantize_qty(qty, self.step_size)

    def meets_filters(self, price: Decimal, qty: Decimal) -> bool:
        """True si una orden `qty @ price` pasa LOT_SIZE y NOTIONAL."""
        if qty < self.min_qty or (self.max_qty is not None and qty > self.max_qty):
            return False
        return price * qty >= self.min_notional

    def supports_native_stop(self) -> bool:
        """True si el símbolo acepta `STOP_LOSS` de mercado (si no, `STOP_LOSS_LIMIT`)."""
        return "STOP_LOSS" in self.order_types


class RateLimits(BaseModel):
    """Límites publicados en `exchangeInfo.rateLimits`. Defaults = Binance Spot 2026."""

    model_config = ConfigDict(frozen=True)

    request_weight_per_minute: int = Field(default=6000, gt=0)
    orders_per_10s: int = Field(default=100, gt=0)
    orders_per_day: int = Field(default=200_000, gt=0)
    raw_requests_per_5m: int = Field(default=61_000, gt=0)


class CcxtClient(Protocol):
    """Subconjunto de la API de `ccxt.binance` que usa el adapter (duck typing para tests)."""

    def load_markets(self, reload: bool = False) -> dict[str, Any]: ...

    def fetch_time(self) -> int: ...

    def public_get_klines(self, params: dict[str, Any] | None = None) -> list[list[Any]]: ...

    def public_get_exchangeinfo(self, params: dict[str, Any] | None = None) -> dict[str, Any]: ...


# --------------------------------------------------------------------------- errores


def redact(text: str) -> str:
    """Quita query strings de URLs (en endpoints firmados llevan `signature=` y `timestamp`)."""
    return _QUERY_RE.sub("?<query redactada>", text)


def is_ip_ban(exc: Exception) -> bool:
    """418 de Binance: la IP ya está baneada; reintentar solo alarga el castigo."""
    if not isinstance(exc, ccxt.DDoSProtection):
        return False
    text = str(exc)
    return " 418 " in f" {text} " or "banned" in text.lower()


def map_ccxt_error(exc: Exception) -> ExchangeError:
    """Traduce una excepción de ccxt a la jerarquía del dominio, conservando la causa."""
    text = redact(f"{type(exc).__name__}: {exc}")
    mapped: ExchangeError
    if isinstance(exc, ccxt.AuthenticationError):
        mapped = AuthError(text)
    elif isinstance(exc, ccxt.InsufficientFunds):
        mapped = InsufficientFunds(text)
    elif isinstance(exc, ccxt.InvalidOrder | ccxt.BadRequest | ccxt.ArgumentsRequired):
        mapped = InvalidOrder(text)
    elif isinstance(exc, ccxt.RateLimitExceeded | ccxt.DDoSProtection):
        mapped = RateLimited(text)
    elif isinstance(exc, ccxt.OperationFailed):
        mapped = ExchangeUnavailable(text)
    else:
        mapped = ExchangeError(text)
    mapped.__cause__ = exc
    return mapped


def is_retryable(exc: Exception) -> bool:
    """Fallas transitorias: red, timeout, mantenimiento, 429, respuesta rota. Nunca un 418."""
    return isinstance(exc, ccxt.OperationFailed) and not is_ip_ban(exc)


# --------------------------------------------------------------------------- parsing


def _filters_by_type(raw_market: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    filters = raw_market.get("filters") or []
    return {str(f.get("filterType")): dict(f) for f in filters if isinstance(f, Mapping)}


def _clean(value: Decimal) -> Decimal:
    """Sin ceros a la derecha ni notación científica: `0.01000000` → `0.01`, `9000.0` → `9000`."""
    if value == value.to_integral_value():
        return value.quantize(Decimal(1))
    return value.normalize()


def _dec(value: Any, default: str | None = None) -> Decimal | None:
    if value is None:
        value = default
    if value is None:
        return None
    try:
        return _clean(to_decimal(value))
    except (TypeError, ValueError) as exc:
        msg = f"valor numérico inválido del exchange: {value!r}"
        raise ExchangeError(msg) from exc


def parse_market(market: Mapping[str, Any]) -> MarketInfo | None:
    """Convierte un mercado unificado de ccxt en `MarketInfo`.

    Devuelve `None` para mercados que no son spot o cuyo quote no está permitido (ADR-0004).
    Los tamaños se leen de `info.filters` (strings exactos de Binance); si faltan, se cae a los
    valores unificados de ccxt pasando por `to_decimal`.
    """
    if not market.get("spot", True):
        return None
    quote = str(market.get("quote") or "")
    base = str(market.get("base") or "")
    if quote not in ALLOWED_QUOTES or not base:
        return None
    try:
        pair = Pair(base=base, quote=quote)
    except ValueError:
        # Símbolo que el dominio no representa (caracteres fuera de [A-Z0-9]); un mercado raro
        # no debe impedir cargar el resto del universo.
        return None
    info: Mapping[str, Any] = market.get("info") or {}
    filters = _filters_by_type(info)
    precision: Mapping[str, Any] = market.get("precision") or {}
    limits: Mapping[str, Any] = market.get("limits") or {}
    amount_limits: Mapping[str, Any] = limits.get("amount") or {}
    cost_limits: Mapping[str, Any] = limits.get("cost") or {}

    price_filter = filters.get("PRICE_FILTER", {})
    lot_filter = filters.get("LOT_SIZE", {})
    notional_filter = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL") or {}

    tick = _dec(price_filter.get("tickSize")) or _dec(precision.get("price"))
    step = _dec(lot_filter.get("stepSize")) or _dec(precision.get("amount"))
    if tick is None or step is None:
        msg = f"{market.get('symbol')}: sin tickSize/stepSize en el mercado"
        raise ExchangeError(msg)
    min_qty = _dec(lot_filter.get("minQty")) or _dec(amount_limits.get("min"), "0")
    max_qty = _dec(lot_filter.get("maxQty")) or _dec(amount_limits.get("max"))
    min_notional = (
        _dec(notional_filter.get("minNotional"))
        or _dec(notional_filter.get("notional"))
        or _dec(cost_limits.get("min"), "0")
    )
    active = bool(market.get("active", True)) and str(info.get("status", "TRADING")) == "TRADING"
    order_types = tuple(str(t) for t in (info.get("orderTypes") or ()))
    return MarketInfo(
        pair=pair,
        tick_size=tick,
        step_size=step,
        min_qty=min_qty or Decimal(0),
        max_qty=max_qty,
        min_notional=min_notional or Decimal(0),
        active=active,
        order_types=order_types,
    )


def parse_rate_limits(exchange_info: Mapping[str, Any]) -> RateLimits:
    """Lee `rateLimits` de `exchangeInfo`; los que no aparezcan conservan el default."""
    values: dict[str, int] = {}
    for entry in exchange_info.get("rateLimits") or []:
        kind = entry.get("rateLimitType")
        interval = entry.get("interval")
        num = int(entry.get("intervalNum", 1))
        limit = int(entry.get("limit", 0))
        if limit <= 0:
            continue
        if kind == "REQUEST_WEIGHT" and interval == "MINUTE" and num == 1:
            values["request_weight_per_minute"] = limit
        elif kind == "ORDERS" and interval == "SECOND" and num == 10:
            values["orders_per_10s"] = limit
        elif kind == "ORDERS" and interval == "DAY" and num == 1:
            values["orders_per_day"] = limit
        elif kind == "RAW_REQUESTS" and interval == "MINUTE" and num == 5:
            values["raw_requests_per_5m"] = limit
    return RateLimits(**values)


def parse_kline_row(row: list[Any], pair: Pair, timeframe: Timeframe) -> Candle:
    """Kline cruda de Binance → `Candle`.

    Formato: `[openTime, open, high, low, close, volume, closeTime, quoteVolume, trades, ...]`
    con los montos como **string**; `to_decimal` los toma tal cual (sin float en el medio).
    """
    if len(row) < 6:
        msg = f"kline incompleta para {pair}: {row!r}"
        raise ExchangeError(msg)
    try:
        return Candle(
            pair=pair,
            timeframe=timeframe,
            open_time=int(row[0]),
            open=to_decimal(row[1]),
            high=to_decimal(row[2]),
            low=to_decimal(row[3]),
            close=to_decimal(row[4]),
            volume=to_decimal(row[5]),
        )
    except (TypeError, ValueError) as exc:
        msg = f"kline inválida para {pair}: {row!r}: {exc}"
        raise ExchangeError(msg) from exc


# --------------------------------------------------------------------------- adapter


def _local_now_ms() -> int:
    return int(time.time() * 1000)


class BinanceExchange:
    """Fachada síncrona sobre un cliente ccxt con retry, mapeo de errores y reloj del exchange."""

    def __init__(
        self,
        client: CcxtClient,
        *,
        max_retries: int = 5,
        backoff_base_s: float = 1.0,
        backoff_max_s: float = 30.0,
        rate_limit_min_wait_s: float = 5.0,
        sleep: Callable[[float], None] = time.sleep,
        local_now_ms: Callable[[], int] = _local_now_ms,
        offset_refresh_ms: int = TIME_OFFSET_REFRESH_MS,
    ) -> None:
        self._client = client
        self._max_retries = max_retries
        self._backoff_base_s = backoff_base_s
        self._backoff_max_s = backoff_max_s
        self._rate_limit_min_wait_s = rate_limit_min_wait_s
        self._sleep = sleep
        self._local_now_ms = local_now_ms
        self._offset_refresh_ms = offset_refresh_ms
        self._markets: dict[Pair, MarketInfo] | None = None
        self._rate_limits: RateLimits | None = None
        self._offset_ms: int | None = None
        self._offset_measured_at: int = 0

    @classmethod
    def create(
        cls,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,
        timeout_ms: int = 10_000,
        recv_window_ms: int = 10_000,
        sandbox: bool = False,
    ) -> BinanceExchange:
        """Construye el cliente ccxt real. Sin claves solo sirve para endpoints públicos."""
        options: dict[str, Any] = {
            "enableRateLimit": True,
            "timeout": timeout_ms,
            "options": {
                "defaultType": "spot",
                "recvWindow": recv_window_ms,
                "adjustForTimeDifference": True,
            },
        }
        if api_key and api_secret:
            options["apiKey"] = api_key
            options["secret"] = api_secret
        client = ccxt.binance(options)
        if sandbox:
            client.set_sandbox_mode(True)
        return cls(client)

    # ----------------------------------------------------------------- retry

    def _call(self, description: str, fn: Callable[[], Any]) -> Any:
        """Ejecuta `fn` reintentando solo errores transitorios; el resto se mapea y propaga."""
        attempt = 0
        while True:
            try:
                return fn()
            except ccxt.BaseError as exc:
                if not is_retryable(exc) or attempt >= self._max_retries:
                    raise map_ccxt_error(exc) from exc
                wait = min(self._backoff_base_s * (2**attempt), self._backoff_max_s)
                if isinstance(exc, ccxt.RateLimitExceeded | ccxt.DDoSProtection):
                    wait = max(wait, self._rate_limit_min_wait_s, self._retry_after_s())
                attempt += 1
                log.warning(
                    "%s: %s; reintento %d/%d en %.1f s",
                    description,
                    redact(f"{type(exc).__name__}: {exc}"),
                    attempt,
                    self._max_retries,
                    wait,
                )
                self._sleep(wait)

    def _retry_after_s(self) -> float:
        """`Retry-After` de la última respuesta, si ccxt lo expone; 0 si no."""
        headers = getattr(self._client, "last_response_headers", None) or {}
        raw = headers.get("Retry-After") or headers.get("retry-after")
        try:
            return float(raw) if raw is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    # ----------------------------------------------------------------- mercados

    def load_markets(self, reload: bool = False) -> dict[Pair, MarketInfo]:
        """Mercados spot con quote permitido. Cacheado hasta `reload=True`."""
        if self._markets is None or reload:
            raw = self._call("load_markets", lambda: self._client.load_markets(reload))
            markets: dict[Pair, MarketInfo] = {}
            for market in raw.values():
                parsed = parse_market(market)
                if parsed is not None:
                    markets[parsed.pair] = parsed
            self._markets = markets
            log.info("load_markets: %d mercados spot con quote permitido", len(markets))
        return dict(self._markets)

    def market(self, pair: Pair) -> MarketInfo:
        markets = self.load_markets()
        try:
            return markets[pair]
        except KeyError as exc:
            msg = f"{pair} no está listado en Binance Spot con quote permitido"
            raise ExchangeError(msg) from exc

    def rate_limits(self, reload: bool = False) -> RateLimits:
        """Límites reales de `exchangeInfo` (peso 20). Cacheado."""
        if self._rate_limits is None or reload:
            info = self._call("exchangeInfo", lambda: self._client.public_get_exchangeinfo())
            self._rate_limits = parse_rate_limits(info)
        return self._rate_limits

    # ----------------------------------------------------------------- reloj

    def fetch_time(self) -> int:
        """Hora del servidor en ms (sin cache)."""
        return int(self._call("fetch_time", self._client.fetch_time))

    def time_offset_ms(self, force: bool = False) -> int:
        """`server − local`, medido contra el punto medio de la ida y vuelta; cache de una hora."""
        now = self._local_now_ms()
        stale = self._offset_ms is None or now - self._offset_measured_at >= self._offset_refresh_ms
        if force or stale:
            t0 = self._local_now_ms()
            server = self.fetch_time()
            t1 = self._local_now_ms()
            self._offset_ms = server - (t0 + t1) // 2
            self._offset_measured_at = t1
            log.debug("offset de reloj vs Binance: %+d ms", self._offset_ms)
        assert self._offset_ms is not None
        return self._offset_ms

    def now_ms(self) -> int:
        """Hora actual según el reloj del exchange (local + offset cacheado)."""
        return self._local_now_ms() + self.time_offset_ms()

    # ----------------------------------------------------------------- OHLCV

    def fetch_ohlcv_page(
        self, pair: Pair, timeframe: Timeframe, since_ms: int, limit: int = OHLCV_PAGE_LIMIT
    ) -> list[Candle]:
        """Una sola request de hasta `limit` klines desde `since_ms` (inclusive), ordenadas."""
        if not 1 <= limit <= OHLCV_PAGE_LIMIT:
            msg = f"limit debe estar en [1, {OHLCV_PAGE_LIMIT}], recibido {limit}"
            raise ValueError(msg)
        params = {
            "symbol": pair.binance_symbol,
            "interval": timeframe.value,
            "startTime": since_ms,
            "limit": limit,
        }
        rows = self._call(
            f"klines {pair} {timeframe.value}", lambda: self._client.public_get_klines(params)
        )
        candles = [parse_kline_row(row, pair, timeframe) for row in rows]
        candles.sort(key=lambda c: c.open_time)
        return candles

    def iter_ohlcv_pages(
        self,
        pair: Pair,
        timeframe: Timeframe,
        since_ms: int,
        until_ms: int | None = None,
        *,
        page_limit: int = OHLCV_PAGE_LIMIT,
        max_pages: int | None = None,
    ) -> Iterator[list[Candle]]:
        """Páginas de velas con `since_ms ≤ open_time < until_ms`, hacia adelante.

        Con `until_ms` definido solo termina por página vacía o por alcanzar `until_ms`: una
        página corta intermedia no corta la descarga (cuesta a lo sumo una request extra).
        Sin `until_ms` (hasta el presente), una página corta significa "no hay más".
        """
        if since_ms < 0:
            msg = f"since_ms negativo: {since_ms}"
            raise ValueError(msg)
        cursor = since_ms
        pages = 0
        while until_ms is None or cursor < until_ms:
            if max_pages is not None and pages >= max_pages:
                return
            page = self.fetch_ohlcv_page(pair, timeframe, cursor, page_limit)
            pages += 1
            if not page:
                return
            kept = [c for c in page if until_ms is None or c.open_time < until_ms]
            if kept:
                yield kept
            next_cursor = page[-1].open_time + timeframe.ms
            if next_cursor <= cursor or (until_ms is None and len(page) < page_limit):
                return
            cursor = next_cursor

    def fetch_ohlcv(
        self,
        pair: Pair,
        timeframe: Timeframe,
        since_ms: int,
        until_ms: int | None = None,
        *,
        page_limit: int = OHLCV_PAGE_LIMIT,
        max_pages: int | None = None,
    ) -> list[Candle]:
        """Todas las velas de `iter_ohlcv_pages`, deduplicadas por `open_time` y ordenadas.

        Puede incluir la vela en formación si `until_ms` no la excluye: descartarla es
        responsabilidad del `Downloader`, que conoce el reloj del exchange.
        """
        result: dict[int, Candle] = {}
        for page in self.iter_ohlcv_pages(
            pair, timeframe, since_ms, until_ms, page_limit=page_limit, max_pages=max_pages
        ):
            for candle in page:
                result[candle.open_time] = candle
        return [result[k] for k in sorted(result)]


# --------------------------------------------------------------------------- snapshot


class MarketsSnapshot(BaseModel):
    """Mercados y límites congelados para tests y backtests sin red."""

    model_config = ConfigDict(frozen=True)

    version: int = SNAPSHOT_VERSION
    exchange: str = EXCHANGE_ID
    fetched_at: str
    source: str
    rate_limits: RateLimits = RateLimits()
    markets: tuple[MarketInfo, ...]

    def by_pair(self) -> dict[Pair, MarketInfo]:
        return {m.pair: m for m in self.markets}


def default_snapshot_path() -> Path:
    """Ruta del snapshot empaquetado con el código (válida mientras el paquete viva en disco)."""
    with resources.as_file(resources.files("tradingbot.exchange") / SNAPSHOT_FILENAME) as path:
        return Path(path)


def load_markets_snapshot(path: Path | None = None) -> MarketsSnapshot:
    """Lee el snapshot (por defecto el empaquetado). Los montos vienen como strings JSON."""
    if path is None:
        text = (resources.files("tradingbot.exchange") / SNAPSHOT_FILENAME).read_text("utf-8")
    else:
        text = path.read_text(encoding="utf-8")
    return MarketsSnapshot.model_validate(json.loads(text))


def build_markets_snapshot(
    exchange: BinanceExchange,
    pairs: tuple[Pair, ...] | None = None,
    *,
    source: str = "binance exchangeInfo",
    reload: bool = False,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> MarketsSnapshot:
    """Arma un snapshot desde el exchange (todos los mercados o solo `pairs`).

    `reload=False` reutiliza mercados y límites ya cacheados en el adapter.
    """
    markets = exchange.load_markets(reload=reload)
    if pairs is not None:
        missing = [p.symbol for p in pairs if p not in markets]
        if missing:
            msg = f"pares no listados en Binance Spot: {', '.join(missing)}"
            raise ExchangeError(msg)
        markets = {p: markets[p] for p in pairs}
    ordered = tuple(markets[p] for p in sorted(markets))
    return MarketsSnapshot(
        fetched_at=now().isoformat(timespec="seconds"),
        source=source,
        rate_limits=exchange.rate_limits(reload=reload),
        markets=ordered,
    )


def save_markets_snapshot(snapshot: MarketsSnapshot, path: Path) -> None:
    """Escribe el snapshot en JSON con montos como strings (sin pasar por float), atómico."""
    payload = snapshot.model_dump(mode="json")
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
