"""Posiciones abiertas, trades cerrados y snapshots de portfolio."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbot.domain.enums import ExitReason
from tradingbot.domain.money import ZERO, notional
from tradingbot.domain.orders import CLIENT_ORDER_ID_RE
from tradingbot.domain.pair import Pair


class Position(BaseModel):
    """Posición long abierta. `qty` es la cantidad **neta** en base (tras la fee de entrada).

    `stop_price` y `highest_close_since_entry` se persisten: al reiniciar no se recomputan.
    El stop solo puede subir (`raise_stop`); bajarlo sería aflojar el riesgo ya asumido. Puede
    estar por encima de la entrada (trailing con ganancia asegurada, o gap bajista en el fill),
    por eso no se compara con `entry_price`: esa restricción vive en `OrderIntent`.
    """

    model_config = ConfigDict(frozen=True)

    pair: Pair
    strategy: str = Field(min_length=1)
    qty: Decimal = Field(gt=0)
    entry_price: Decimal = Field(gt=0)
    entry_time: int = Field(ge=0)
    stop_price: Decimal = Field(gt=0)
    highest_close_since_entry: Decimal = Field(gt=0)
    client_order_id: str = Field(pattern=CLIENT_ORDER_ID_RE.pattern)
    entry_fee_quote: Decimal = Field(default=ZERO, ge=0)

    def value(self, price: Decimal) -> Decimal:
        return notional(price, self.qty)

    def unrealized_pnl(self, price: Decimal) -> Decimal:
        """PnL abierto a `price`, neto de la fee de entrada (la de salida se conoce al salir)."""
        return (price - self.entry_price) * self.qty - self.entry_fee_quote

    def risk_at_stop(self) -> Decimal:
        """Pérdida en quote si el stop se ejecuta exactamente a `stop_price`.

        Negativo significa ganancia asegurada (el stop ya está por encima de la entrada).
        """
        return (self.entry_price - self.stop_price) * self.qty

    def with_close(self, close: Decimal) -> Position:
        """Actualiza el máximo cierre desde la entrada (nunca lo baja)."""
        if close <= self.highest_close_since_entry:
            return self
        return self.model_copy(update={"highest_close_since_entry": close})

    def raise_stop(self, stop: Decimal) -> Position:
        """Sube el stop; ignora valores iguales o menores al actual."""
        if stop <= self.stop_price:
            return self
        return self.model_copy(update={"stop_price": stop})


class Trade(BaseModel):
    """Round trip cerrado: una entrada y su salida completa."""

    model_config = ConfigDict(frozen=True)

    pair: Pair
    strategy: str = Field(min_length=1)
    qty: Decimal = Field(gt=0)
    entry_price: Decimal = Field(gt=0)
    entry_time: int = Field(ge=0)
    exit_price: Decimal = Field(gt=0)
    exit_time: int = Field(ge=0)
    exit_reason: ExitReason
    fees_quote: Decimal = Field(ge=0, description="todas las fees del round trip, en quote")
    entry_client_order_id: str = Field(pattern=CLIENT_ORDER_ID_RE.pattern)
    exit_client_order_id: str = Field(pattern=CLIENT_ORDER_ID_RE.pattern)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.exit_time < self.entry_time:
            msg = "exit_time anterior a entry_time"
            raise ValueError(msg)
        return self

    @property
    def gross_pnl(self) -> Decimal:
        return (self.exit_price - self.entry_price) * self.qty

    @property
    def pnl(self) -> Decimal:
        """PnL neto de fees, en quote."""
        return self.gross_pnl - self.fees_quote

    @property
    def pnl_pct(self) -> Decimal:
        """PnL neto sobre la notional neta de entrada (`entry_price × qty neta`).

        Sobrestima en ~fee_rate respecto del capital bruto invertido; se usa como métrica
        relativa entre trades, no para contabilidad.
        """
        return self.pnl / (self.entry_price * self.qty)

    @property
    def duration_ms(self) -> int:
        return self.exit_time - self.entry_time

    @property
    def is_winner(self) -> bool:
        return self.pnl > ZERO


class PortfolioSnapshot(BaseModel):
    """Foto del portfolio al cierre de un `Bar`, con equity mark-to-market.

    `cash` es el quote libre. El quote comprometido en órdenes `PENDING` se modela en la
    Fase 7 (paper/live) como campo aparte; en backtest la orden se llena en el `Bar` siguiente.
    `dust` son restos de base por debajo del `stepSize` que no se pueden vender; se reportan
    aparte y no forman parte del equity operativo.
    """

    model_config = ConfigDict(frozen=True)

    ts: int = Field(ge=0)
    cash: Decimal = Field(ge=0, description="quote libre (no comprometido en órdenes)")
    positions: tuple[Position, ...] = ()
    marks: Mapping[Pair, Decimal] = Field(default_factory=dict)
    dust: Mapping[str, Decimal] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        seen: set[Pair] = set()
        for position in self.positions:
            if position.pair in seen:
                msg = f"dos posiciones abiertas en {position.pair}"
                raise ValueError(msg)
            seen.add(position.pair)
            if position.pair not in self.marks:
                msg = f"falta el precio de marca de {position.pair}"
                raise ValueError(msg)
        return self

    @property
    def positions_value(self) -> Decimal:
        return sum((p.value(self.marks[p.pair]) for p in self.positions), ZERO)

    @property
    def equity(self) -> Decimal:
        return self.cash + self.positions_value

    @property
    def exposure_pct(self) -> Decimal:
        """Fracción del equity invertida en posiciones (0 si no hay equity)."""
        equity = self.equity
        return self.positions_value / equity if equity > ZERO else ZERO

    def position_for(self, pair: Pair) -> Position | None:
        for position in self.positions:
            if position.pair == pair:
                return position
        return None
