"""Puerto `TradeStore` y su implementación en memoria (backtest). `SqliteStore` llega en la Fase 7.

El `Engine` escribe todo lo que pasa (órdenes, fills, posiciones, trades, snapshots de equity y
eventos con `reason_code`); los reportes y el test de paridad leen de acá.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from tradingbot.domain.orders import Fill, Order
from tradingbot.domain.pair import Pair
from tradingbot.domain.positions import PortfolioSnapshot, Position, Trade


@dataclass(frozen=True, slots=True)
class EventRecord:
    """Algo que el bot decidió o rechazó y conviene poder auditar después."""

    ts: int
    kind: str  # p. ej. "entry_rejected", "exit_stuck", "stop_set"
    pair: Pair | None = None
    reason: str = ""
    payload: Mapping[str, str] = field(default_factory=dict)


class TradeStore(Protocol):
    def save_order(self, order: Order) -> None: ...

    def save_fill(self, fill: Fill) -> None: ...

    def save_position(self, position: Position) -> None: ...

    def remove_position(self, pair: Pair) -> None: ...

    def save_trade(self, trade: Trade) -> None: ...

    def snapshot_equity(self, snapshot: PortfolioSnapshot) -> None: ...

    def record_event(self, event: EventRecord) -> None: ...

    def load_open_positions(self) -> tuple[Position, ...]: ...

    def orders(self) -> tuple[Order, ...]: ...

    def fills(self) -> tuple[Fill, ...]: ...

    def trades(self) -> tuple[Trade, ...]: ...

    def snapshots(self) -> tuple[PortfolioSnapshot, ...]: ...

    def events(self) -> tuple[EventRecord, ...]: ...


class InMemoryStore:
    """Todo en listas; una orden se guarda por `client_order_id` (la última versión gana)."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}
        self._fills: list[Fill] = []
        self._positions: dict[Pair, Position] = {}
        self._trades: list[Trade] = []
        self._snapshots: list[PortfolioSnapshot] = []
        self._events: list[EventRecord] = []

    def save_order(self, order: Order) -> None:
        self._orders[order.client_order_id] = order

    def save_fill(self, fill: Fill) -> None:
        self._fills.append(fill)

    def save_position(self, position: Position) -> None:
        self._positions[position.pair] = position

    def remove_position(self, pair: Pair) -> None:
        self._positions.pop(pair, None)

    def save_trade(self, trade: Trade) -> None:
        self._trades.append(trade)

    def snapshot_equity(self, snapshot: PortfolioSnapshot) -> None:
        self._snapshots.append(snapshot)

    def record_event(self, event: EventRecord) -> None:
        self._events.append(event)

    def load_open_positions(self) -> tuple[Position, ...]:
        return tuple(self._positions[p] for p in sorted(self._positions))

    def orders(self) -> tuple[Order, ...]:
        return tuple(self._orders.values())

    def fills(self) -> tuple[Fill, ...]:
        return tuple(self._fills)

    def trades(self) -> tuple[Trade, ...]:
        return tuple(self._trades)

    def snapshots(self) -> tuple[PortfolioSnapshot, ...]:
        return tuple(self._snapshots)

    def events(self) -> tuple[EventRecord, ...]:
        return tuple(self._events)
