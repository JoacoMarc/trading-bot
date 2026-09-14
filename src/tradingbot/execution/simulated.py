"""`SimulatedBroker`: ejecución determinística para backtest (y base del paper de la Fase 7).

Modelo (ADR-0002 §2.1):
- Orden `PENDING` → fill al `open` de la vela siguiente. Compras a `open × (1 + slippage)`,
  ventas a `open × (1 − slippage)`, precio cuantizado al `tickSize`. `ref_price` = `open`.
  Una compra cuyo costo supera el cash libre se **rechaza** (`insufficient_funds`), como haría
  el exchange con `-2010`; el `Engine` la registra y no abre posición.
- Stop en reposo: si `open <= stop` el gap lo atraviesa y se ejecuta al `open` (`fill_ts` =
  open); si no y `low <= stop`, al `stop` en algún momento de la vela (`fill_ts` = close). En
  ambos casos con slippage en contra; `ref_price` = precio teórico.
- Fee en el activo recibido: base en compras (la cantidad neta baja), quote en ventas. Con
  `pay_with_bnb` se simula en quote al `bnb_fee_rate`. Fees cuantizadas a 8 decimales como
  las informa Binance.
- Sin fills parciales en v1. Si un par no está en el `Bar` (hueco), sus órdenes esperan.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal

from tradingbot.config.models import ExecutionConfig
from tradingbot.domain.candle import Bar
from tradingbot.domain.enums import OrderStatus, Side
from tradingbot.domain.errors import DomainError
from tradingbot.domain.money import BPS_DENOMINATOR, ONE, ZERO, quantize_price
from tradingbot.domain.orders import Fill, Order, OrderIntent, make_client_order_id
from tradingbot.domain.pair import Pair
from tradingbot.exchange.binance import MarketInfo
from tradingbot.execution.broker import BrokerEvent, StopOrder

FEE_QUANTUM = Decimal("1e-8")
INSUFFICIENT_FUNDS = "insufficient_funds"


class SimulatedBroker:
    def __init__(
        self,
        execution: ExecutionConfig,
        markets: Mapping[Pair, MarketInfo],
        free_cash: Callable[[], Decimal] | None = None,
    ) -> None:
        self._cfg = execution
        self._markets = dict(markets)
        self._free_cash = free_cash
        self._pending: dict[str, Order] = {}
        self._stops: dict[Pair, StopOrder] = {}
        self._slippage = execution.slippage_bps / BPS_DENOMINATOR

    # ------------------------------------------------------------- consultas

    def market(self, pair: Pair) -> MarketInfo:
        try:
            return self._markets[pair]
        except KeyError as exc:
            msg = f"sin MarketInfo para {pair}"
            raise DomainError(msg) from exc

    def pending_orders(self) -> tuple[Order, ...]:
        return tuple(self._pending.values())

    def get_stop(self, pair: Pair) -> StopOrder | None:
        return self._stops.get(pair)

    def bind_cash(self, free_cash: Callable[[], Decimal]) -> None:
        """Conecta la consulta de cash libre (el `Engine` la provee al construirse)."""
        self._free_cash = free_cash

    # ------------------------------------------------------------- órdenes y stops

    def submit(self, intent: OrderIntent, ts: int) -> Order:
        if intent.client_order_id in self._pending:
            msg = f"orden {intent.client_order_id} ya pendiente"
            raise DomainError(msg)
        self.market(intent.pair)  # valida que el par sea operable
        order = Order(intent=intent, status=OrderStatus.PENDING, created_ts=ts, updated_ts=ts)
        self._pending[intent.client_order_id] = order
        return order

    def set_stop(self, stop: StopOrder) -> None:
        self._stops[stop.pair] = stop

    def cancel_stop(self, pair: Pair) -> StopOrder | None:
        return self._stops.pop(pair, None)

    # ------------------------------------------------------------- eventos por vela

    def on_bar_open(self, bar: Bar) -> list[BrokerEvent]:
        events: list[BrokerEvent] = []
        available = self._free_cash() if self._free_cash is not None else None
        for cid in list(self._pending):
            order = self._pending[cid]
            candle = bar.get(order.intent.pair)
            if candle is None:
                continue  # hueco de datos: la orden espera a la próxima vela del par
            event, spent = self._settle(
                order, ref_price=candle.open, fill_ts=candle.open_time, available=available
            )
            if available is not None:
                available -= spent
            events.append(event)
        return events

    def _settle(
        self, order: Order, *, ref_price: Decimal, fill_ts: int, available: Decimal | None
    ) -> tuple[BrokerEvent, Decimal]:
        """Llena (o rechaza por cash) una orden pendiente. Devuelve el evento y el cash gastado."""
        fill = self._fill_market(order.intent, ref_price=ref_price, fill_ts=fill_ts)
        del self._pending[order.client_order_id]
        if order.intent.side is Side.BUY and available is not None:
            cost = fill.notional + (fill.fee_amount if fill.fee_asset == fill.pair.quote else 0)
            if cost > available:
                rejected = order.with_status(
                    OrderStatus.REJECTED,
                    ts=fill_ts,
                    reason=f"{INSUFFICIENT_FUNDS}: costo {cost} > cash libre {available}",
                )
                return BrokerEvent(order=rejected, fill=None), ZERO
            return BrokerEvent(order=order.with_fill(fill, ts=fill_ts), fill=fill), cost
        return BrokerEvent(order=order.with_fill(fill, ts=fill_ts), fill=fill), ZERO

    def on_bar(self, bar: Bar) -> list[BrokerEvent]:
        events: list[BrokerEvent] = []
        for pair in list(self._stops):
            stop = self._stops[pair]
            candle = bar.get(pair)
            if candle is None:
                continue
            if candle.open <= stop.stop_price:
                trigger, fill_ts = candle.open, candle.open_time  # gap a través del stop
            elif candle.low <= stop.stop_price:
                trigger, fill_ts = stop.stop_price, candle.close_time
            else:
                continue
            intent = OrderIntent(
                client_order_id=make_client_order_id(
                    stop.strategy, pair, candle.open_time, Side.SELL, stop.exit_reason
                ),
                strategy=stop.strategy,
                pair=pair,
                side=Side.SELL,
                qty=stop.qty,
                decision_price=stop.stop_price,
                signal_ts=stop.signal_ts,
                decision_ts=candle.open_time,
                exit_reason=stop.exit_reason,
                note="stop en reposo",
            )
            order = Order(
                intent=intent,
                status=OrderStatus.PENDING,
                created_ts=candle.open_time,
                updated_ts=candle.open_time,
            )
            fill = self._fill_market(intent, ref_price=trigger, fill_ts=fill_ts)
            del self._stops[pair]
            events.append(BrokerEvent(order=order.with_fill(fill, ts=fill.fill_ts), fill=fill))
        return events

    # ------------------------------------------------------------- modelo de fill

    def _fill_market(self, intent: OrderIntent, *, ref_price: Decimal, fill_ts: int) -> Fill:
        market = self.market(intent.pair)
        if intent.side is Side.BUY:
            raw = ref_price * (ONE + self._slippage)
            price = quantize_price(raw, market.tick_size, ROUND_UP)
        else:
            raw = ref_price * (ONE - self._slippage)
            price = quantize_price(raw, market.tick_size, ROUND_DOWN)
        price = max(price, market.tick_size)
        notional = price * intent.qty
        if self._cfg.pay_with_bnb:
            fee_asset, fee_amount = intent.pair.quote, notional * self._cfg.bnb_fee_rate
        elif intent.side is Side.BUY:
            fee_asset, fee_amount = intent.pair.base, intent.qty * self._cfg.fee_rate
        else:
            fee_asset, fee_amount = intent.pair.quote, notional * self._cfg.fee_rate
        return Fill(
            client_order_id=intent.client_order_id,
            pair=intent.pair,
            side=intent.side,
            price=price,
            qty=intent.qty,
            fee_amount=fee_amount.quantize(FEE_QUANTUM, rounding=ROUND_HALF_UP),
            fee_asset=fee_asset,
            ref_price=ref_price,
            signal_ts=intent.signal_ts,
            decision_ts=intent.decision_ts,
            fill_ts=fill_ts,
        )
