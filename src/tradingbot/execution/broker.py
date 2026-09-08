"""Puerto `Broker` (ADR-0002): la misma interfaz para simulado, paper y live.

El `Engine` llama, por cada `Bar` cerrado y en este orden:
1. `on_bar_open(bar)`: fills de las órdenes `PENDING` al open de la vela.
2. `on_bar(bar)`: ejecución de stops en reposo con el rango de la vela.
Después de decidir, `submit(intent)` deja órdenes `PENDING` para el bar siguiente y
`set_stop`/`cancel_stop` mantienen el stop en reposo de cada posición.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from tradingbot.domain.candle import Bar
from tradingbot.domain.enums import ExitReason
from tradingbot.domain.orders import Fill, Order, OrderIntent
from tradingbot.domain.pair import Pair


@dataclass(frozen=True, slots=True)
class StopOrder:
    """Stop en reposo para la posición de un par."""

    pair: Pair
    stop_price: Decimal
    qty: Decimal
    exit_reason: ExitReason  # STOP (inicial) o TRAILING (ya subido al menos una vez)
    strategy: str
    signal_ts: int


@dataclass(frozen=True, slots=True)
class BrokerEvent:
    """Resultado del broker para una orden: su fill, o `fill=None` si la rechazó."""

    order: Order
    fill: Fill | None


class Broker(Protocol):
    def submit(self, intent: OrderIntent, ts: int) -> Order:
        """Acepta la intención y devuelve la orden `PENDING`."""
        ...

    def set_stop(self, stop: StopOrder) -> None:
        """Crea o reemplaza el stop en reposo del par."""
        ...

    def cancel_stop(self, pair: Pair) -> StopOrder | None:
        """Retira el stop en reposo (antes de vender por señal). Devuelve el retirado."""
        ...

    def get_stop(self, pair: Pair) -> StopOrder | None: ...

    def pending_orders(self) -> tuple[Order, ...]: ...

    def on_bar_open(self, bar: Bar) -> list[BrokerEvent]:
        """Llena las órdenes pendientes al open de la vela (+ slippage)."""
        ...

    def on_bar(self, bar: Bar) -> list[BrokerEvent]:
        """Ejecuta los stops que la vela tocó (gap al open o `low <= stop`)."""
        ...
