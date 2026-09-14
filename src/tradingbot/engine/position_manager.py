"""`PositionManager`: abre y cierra posiciones a partir de fills y mantiene el stop en reposo.

Reglas (ADR-0002): el stop inicial se re-ancla al precio real del fill conservando la distancia
`close(t) − stop` de la señal; el trailing solo sube; el `Broker` ejecuta los stops, acá solo
se calculan y publican los niveles. Un stop que el exchange no aceptaría (cantidad bajo `minQty`
o notional bajo `minNotional`) no se publica y la posición queda marcada sin protección.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal

from tradingbot.domain.enums import ExitReason
from tradingbot.domain.errors import DomainError
from tradingbot.domain.money import ZERO
from tradingbot.domain.orders import Fill, OrderIntent
from tradingbot.domain.pair import Pair
from tradingbot.domain.positions import Position, Trade
from tradingbot.exchange.binance import MarketInfo
from tradingbot.execution.broker import Broker, StopOrder
from tradingbot.persistence.store import EventRecord, TradeStore
from tradingbot.risk.sizing import sellable_qty


class PositionManager:
    def __init__(
        self, broker: Broker, store: TradeStore, markets: Mapping[Pair, MarketInfo]
    ) -> None:
        self._broker = broker
        self._store = store
        self._markets = markets
        self._positions: dict[Pair, Position] = {}
        self.unprotected: set[Pair] = set()  # posiciones cuyo stop no pasa los filtros

    # ------------------------------------------------------------- consultas

    @property
    def positions(self) -> dict[Pair, Position]:
        return dict(self._positions)

    def get(self, pair: Pair) -> Position | None:
        return self._positions.get(pair)

    def __len__(self) -> int:
        return len(self._positions)

    # ------------------------------------------------------------- recuperación (ADR-0011)

    def restore(self, positions: Iterable[Position], ts: int) -> None:
        """Carga posiciones persistidas y vuelve a publicar sus stops en el broker."""
        for position in positions:
            if position.pair in self._positions:
                msg = f"posición duplicada al restaurar: {position.pair}"
                raise DomainError(msg)
            self._positions[position.pair] = position
            reason = (
                ExitReason.TRAILING
                if position.stop_price > position.entry_price
                else ExitReason.STOP
            )
            self._publish_stop(position, reason, ts)

    # ------------------------------------------------------------- apertura y cierre

    def open_from_fill(self, intent: OrderIntent, fill: Fill) -> Position:
        if intent.pair in self._positions:
            msg = f"ya hay una posición abierta en {intent.pair}"
            raise DomainError(msg)
        if intent.stop_price is None:
            msg = f"la compra {intent.client_order_id} no trae stop"
            raise DomainError(msg)
        distance = intent.decision_price - intent.stop_price
        stop = fill.price - distance
        if stop <= ZERO:  # gap enorme: conservar la proporción en vez de la distancia
            stop = fill.price * (intent.stop_price / intent.decision_price)
        position = Position(
            pair=intent.pair,
            strategy=intent.strategy,
            qty=fill.net_base_qty,
            entry_price=fill.price,
            entry_time=fill.fill_ts,
            stop_price=stop,
            highest_close_since_entry=fill.price,
            client_order_id=intent.client_order_id,
            entry_fee_quote=fill.fee_in_quote(),
        )
        self._positions[position.pair] = position
        self._store.save_position(position)
        self._publish_stop(position, ExitReason.STOP, fill.signal_ts)
        return position

    def close_from_fill(self, fill: Fill, exit_reason: ExitReason) -> Trade:
        position = self._positions.pop(fill.pair, None)
        if position is None:
            msg = f"venta de {fill.pair} sin posición abierta"
            raise DomainError(msg)
        self.unprotected.discard(fill.pair)
        self._broker.cancel_stop(fill.pair)
        trade = Trade(
            pair=position.pair,
            strategy=position.strategy,
            qty=fill.qty,
            entry_price=position.entry_price,
            entry_time=position.entry_time,
            exit_price=fill.price,
            exit_time=fill.fill_ts,
            exit_reason=exit_reason,
            fees_quote=position.entry_fee_quote + fill.fee_in_quote(),
            entry_client_order_id=position.client_order_id,
            exit_client_order_id=fill.client_order_id,
        )
        self._store.remove_position(position.pair)
        self._store.save_trade(trade)
        return trade

    # ------------------------------------------------------------- por vela

    def mark(self, pair: Pair, close: Decimal) -> Position | None:
        position = self._positions.get(pair)
        if position is None:
            return None
        updated = position.with_close(close)
        if updated is not position:
            self._positions[pair] = updated
            self._store.save_position(updated)
        return updated

    def update_trailing(self, pair: Pair, level: Decimal | None, ts: int) -> bool:
        """Sube el stop si el nivel propuesto es mayor. Devuelve True si cambió."""
        position = self._positions.get(pair)
        if position is None or level is None or level <= position.stop_price:
            return False
        raised = position.raise_stop(level)
        self._positions[pair] = raised
        self._store.save_position(raised)
        self._publish_stop(raised, ExitReason.TRAILING, ts)
        return True

    def _publish_stop(self, position: Position, reason: ExitReason, signal_ts: int) -> bool:
        market = self._markets[position.pair]
        qty, _dust = sellable_qty(position.qty, market)
        if qty <= ZERO or qty < market.min_qty or qty * position.stop_price < market.min_notional:
            self.unprotected.add(position.pair)
            self._broker.cancel_stop(position.pair)
            self._store.record_event(
                EventRecord(
                    ts=signal_ts,
                    kind="stop_unpublishable",
                    pair=position.pair,
                    reason="filtros del exchange",
                    payload={"qty": str(qty), "stop": str(position.stop_price)},
                )
            )
            return False
        self.unprotected.discard(position.pair)
        self._broker.set_stop(
            StopOrder(
                pair=position.pair,
                stop_price=position.stop_price,
                qty=qty,
                exit_reason=reason,
                strategy=position.strategy,
                signal_ts=signal_ts,
            )
        )
        return True
