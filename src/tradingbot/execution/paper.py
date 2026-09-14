"""`PaperBroker` + `StopWatcher`: ejecución simulada con precios en vivo (ADR-0011).

Misma matemática que `SimulatedBroker` (slippage en contra, tick, fee en el activo recibido,
`insufficient_funds`); cambia solo **cuándo y con qué precio de referencia** se llena:

- `fill_pending(forming_open_time)`: las órdenes `PENDING` decididas al cierre de `t` se llenan
  enseguida al `open` de la vela en formación `t+1` (leído del exchange; si esa vela todavía no
  imprimió, al último precio operado, que es el mismo dato). `ref_price` = ese open, `fill_ts` =
  hora del exchange. Si el exchange no responde, la orden espera y `on_bar_open(t+1)` la llena
  al `open` de esa vela: el mismo precio, cuatro horas más tarde y sin stop en el medio.
- `check_stops()`: el `StopWatcher` lo llama cada `stop_watch_interval_s`. Si el último precio
  está en o bajo el stop en reposo, vende al último precio con slippage (emula la orden nativa
  de la Fase 10). Al cierre de cada vela `on_bar` aplica además la regla de gap/toque con el
  `low` de la vela cerrada, por si el watcher no vio el toque.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from decimal import Decimal
from typing import Protocol

from tradingbot.config.models import ExecutionConfig
from tradingbot.domain.candle import Candle
from tradingbot.domain.enums import OrderStatus, Side
from tradingbot.domain.errors import ExchangeError
from tradingbot.domain.orders import Order, OrderIntent, make_client_order_id
from tradingbot.domain.pair import Pair
from tradingbot.domain.timeframe import Timeframe
from tradingbot.exchange.binance import MarketInfo
from tradingbot.execution.broker import BrokerEvent
from tradingbot.execution.simulated import SimulatedBroker

log = logging.getLogger(__name__)

AsyncSleep = Callable[[float], Awaitable[None]]


class PriceSource(Protocol):
    """Lo que el paper necesita del exchange (`BinanceExchange` lo cumple)."""

    def now_ms(self) -> int: ...

    def fetch_last_price(self, pair: Pair) -> Decimal: ...

    def fetch_ohlcv_page(
        self, pair: Pair, timeframe: Timeframe, since_ms: int, limit: int = 1000
    ) -> list[Candle]: ...


class PaperBroker(SimulatedBroker):
    def __init__(
        self,
        execution: ExecutionConfig,
        markets: Mapping[Pair, MarketInfo],
        prices: PriceSource,
        timeframe: Timeframe,
        free_cash: Callable[[], Decimal] | None = None,
    ) -> None:
        super().__init__(execution, markets, free_cash)
        self._prices = prices
        self._timeframe = timeframe
        self.price_errors = 0

    # ------------------------------------------------------------- fills inmediatos

    def _forming_open(self, pair: Pair, open_time: int) -> Decimal | None:
        """`open` de la vela en formación, o el último precio si todavía no imprimió."""
        try:
            page = self._prices.fetch_ohlcv_page(pair, self._timeframe, open_time, 1)
            if page and page[0].open_time == open_time:
                return page[0].open
            return self._prices.fetch_last_price(pair)
        except ExchangeError as exc:
            self.price_errors += 1
            log.warning("paper: sin precio para %s (%s); la orden espera", pair.symbol, exc)
            return None

    def fill_pending(self, forming_open_time: int) -> list[BrokerEvent]:
        """Llena las órdenes `PENDING` al open de la vela `forming_open_time` (ADR-0011)."""
        self._timeframe.check_aligned(forming_open_time)
        events: list[BrokerEvent] = []
        available = self._free_cash() if self._free_cash is not None else None
        now = self._prices.now_ms()
        opens: dict[Pair, Decimal | None] = {}
        for cid in list(self._pending):
            order = self._pending[cid]
            pair = order.intent.pair
            if pair not in opens:
                opens[pair] = self._forming_open(pair, forming_open_time)
            ref = opens[pair]
            if ref is None:
                continue
            event, spent = self._settle(order, ref_price=ref, fill_ts=now, available=available)
            if available is not None:
                available -= spent
            events.append(event)
        return events

    # ------------------------------------------------------------- stops entre cierres

    def check_stops(self) -> list[BrokerEvent]:
        """Ejecuta los stops en reposo cuyo último precio está en o bajo el stop."""
        if not self._stops:
            return []
        events: list[BrokerEvent] = []
        now = self._prices.now_ms()
        forming = self._timeframe.floor(now)
        for pair in list(self._stops):
            stop = self._stops[pair]
            try:
                last = self._prices.fetch_last_price(pair)
            except ExchangeError as exc:
                self.price_errors += 1
                log.warning("paper: sin último precio para %s (%s)", pair.symbol, exc)
                continue
            if last > stop.stop_price:
                continue
            intent = OrderIntent(
                client_order_id=make_client_order_id(
                    stop.strategy, pair, forming, Side.SELL, stop.exit_reason
                ),
                strategy=stop.strategy,
                pair=pair,
                side=Side.SELL,
                qty=stop.qty,
                decision_price=stop.stop_price,
                signal_ts=stop.signal_ts,
                decision_ts=now,
                exit_reason=stop.exit_reason,
                note="stop en reposo (watcher)",
            )
            order = Order(intent=intent, status=OrderStatus.PENDING, created_ts=now, updated_ts=now)
            fill = self._fill_market(intent, ref_price=last, fill_ts=now)
            del self._stops[pair]
            events.append(BrokerEvent(order=order.with_fill(fill, ts=now), fill=fill))
        return events


class StopWatcher:
    """Tarea asyncio: cada `interval_s` consulta el último precio y ejecuta stops tocados."""

    def __init__(
        self,
        broker: PaperBroker,
        interval_s: float,
        on_events: Callable[[list[BrokerEvent]], None],
        *,
        sleep: AsyncSleep = asyncio.sleep,
    ) -> None:
        if interval_s <= 0:
            msg = f"interval_s debe ser positivo, recibido {interval_s}"
            raise ValueError(msg)
        self._broker = broker
        self._interval_s = interval_s
        self._on_events = on_events
        self._sleep = sleep
        self._stopped = False
        self.ticks = 0

    def stop(self) -> None:
        self._stopped = True

    def tick(self) -> list[BrokerEvent]:
        """Una pasada (también la usa el runner justo después de cada cierre)."""
        self.ticks += 1
        events = self._broker.check_stops()
        if events:
            self._on_events(events)
        return events

    async def run(self) -> None:
        while True:
            await self._sleep(self._interval_s)
            if self._stopped:  # `stop()` pudo llegar durante la espera
                return
            self.tick()
