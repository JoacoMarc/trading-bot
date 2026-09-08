"""Enumeraciones del dominio."""

from __future__ import annotations

from enum import StrEnum


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LOSS_LIMIT = "stop_loss_limit"


class OrderStatus(StrEnum):
    PENDING = "pending"  # aceptada por el broker, todavía sin enviar/llenar
    OPEN = "open"  # en el exchange, sin fills
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL


_TERMINAL = frozenset(
    {OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED, OrderStatus.EXPIRED}
)


class SignalAction(StrEnum):
    ENTER_LONG = "enter_long"
    EXIT_LONG = "exit_long"
    HOLD = "hold"


class ExitReason(StrEnum):
    STOP = "stop"  # stop inicial
    TRAILING = "trailing"  # trailing stop
    SIGNAL = "signal"  # señal de salida de la estrategia
    FLATTEN = "flatten"  # kill switch con --flatten o cierre manual
    RISK = "risk"  # decisión del RiskManager (p. ej. circuit breaker con flatten)
