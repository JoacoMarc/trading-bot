"""Dimensionamiento por riesgo fijo (PLAN §2.2).

`qty = equity × risk_per_trade / (precio − stop)`, con tope `max_position_pct × cash libre` en
notional (incluido slippage y, si la fee va en quote, la fee), cuantizado al `stepSize` y sujeto
a `minQty` y `minNotional`. Todo en Decimal (ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from tradingbot.domain.money import ZERO, quantize_qty
from tradingbot.exchange.binance import MarketInfo


class ReasonCode(StrEnum):
    """Por qué el `RiskManager` rechazó (o no pudo dimensionar) una operación."""

    MAX_POSITIONS = "max_positions"
    EXPOSURE_LIMIT = "exposure_limit"
    ALREADY_IN_POSITION = "already_in_position"
    PENDING_ORDER = "pending_order"
    INVALID_STOP = "invalid_stop"
    NO_CASH = "no_cash"
    MIN_QTY = "min_qty"
    MIN_NOTIONAL = "min_notional"
    # Protecciones dinámicas (ADR-0007); solo aplican a entradas.
    KILL_SWITCH = "kill_switch"
    DRAWDOWN_HALT = "drawdown_halt"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    PAIR_COOLDOWN = "pair_cooldown"
    MARKET_FILTER = "market_filter"
    REPLAY = "replay"  # Bar de reposición tras un reinicio (ADR-0011): sin entradas


@dataclass(frozen=True, slots=True)
class SizingResult:
    qty: Decimal | None
    notional: Decimal
    reason: ReasonCode | None = None
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.qty is not None


def size_by_risk(
    *,
    equity: Decimal,
    cash_available: Decimal,
    price: Decimal,
    stop: Decimal,
    risk_per_trade: Decimal,
    max_position_pct: Decimal,
    cost_factor: Decimal,
    market: MarketInfo,
) -> SizingResult:
    """Cantidad a comprar para arriesgar `risk_per_trade` del equity si el stop se ejecuta.

    `cost_factor` es cuánto cash cuesta un notional de 1 (1 + slippage, más la fee si va en
    quote). Devuelve `qty=None` con el `ReasonCode` cuando no hay operación válida.
    """
    distance = price - stop
    if distance <= ZERO:
        return SizingResult(None, ZERO, ReasonCode.INVALID_STOP, f"stop {stop} >= precio {price}")
    if cash_available <= ZERO or equity <= ZERO:
        return SizingResult(None, ZERO, ReasonCode.NO_CASH, f"cash libre {cash_available}")

    qty_by_risk = equity * risk_per_trade / distance
    budget = cash_available * max_position_pct
    qty_by_budget = budget / (price * cost_factor)
    qty = quantize_qty(min(qty_by_risk, qty_by_budget), market.step_size)

    if qty <= ZERO or qty < market.min_qty:
        return SizingResult(None, ZERO, ReasonCode.MIN_QTY, f"qty {qty} < minQty {market.min_qty}")
    if market.max_qty is not None and qty > market.max_qty:
        qty = quantize_qty(market.max_qty, market.step_size)
    notional = price * qty
    if notional < market.min_notional:
        return SizingResult(
            None, notional, ReasonCode.MIN_NOTIONAL, f"notional {notional} < {market.min_notional}"
        )
    return SizingResult(qty, notional)


def sellable_qty(position_qty: Decimal, market: MarketInfo) -> tuple[Decimal, Decimal]:
    """Cantidad vendible (cuantizada hacia abajo) y dust que queda en la cuenta."""
    qty = quantize_qty(position_qty, market.step_size)
    return qty, position_qty - qty


def size_by_fraction(
    *,
    equity: Decimal,
    cash_available: Decimal,
    price: Decimal,
    fraction: Decimal,
    cost_factor: Decimal,
    market: MarketInfo,
) -> SizingResult:
    """Tamaño fijo: `fraction` del equity, acotado por el cash libre (ADR-0010).

    Ignora la distancia al stop: el stop es de seguridad y el drawdown se presupuesta con la
    fracción. Mismos filtros del exchange que `size_by_risk`.
    """
    if cash_available <= ZERO or equity <= ZERO:
        return SizingResult(None, ZERO, ReasonCode.NO_CASH, f"cash libre {cash_available}")
    budget = min(equity * fraction, cash_available)
    qty = quantize_qty(budget / (price * cost_factor), market.step_size)
    if qty <= ZERO or qty < market.min_qty:
        return SizingResult(None, ZERO, ReasonCode.MIN_QTY, f"qty {qty} < minQty {market.min_qty}")
    if market.max_qty is not None and qty > market.max_qty:
        qty = quantize_qty(market.max_qty, market.step_size)
    notional = price * qty
    if notional < market.min_notional:
        return SizingResult(
            None, notional, ReasonCode.MIN_NOTIONAL, f"notional {notional} < {market.min_notional}"
        )
    return SizingResult(qty, notional)
