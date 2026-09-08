"""`RiskManager`: slots, exposición, sizing, `minNotional`, ranking y protecciones.

Regla dura 7: nunca bloquea una salida. `exit_intent` solo puede devolver `None` cuando la
cantidad vendible no cumple los filtros del exchange (posición `STUCK`, que el `Engine` reporta).
Las protecciones dinámicas (pérdida diaria, drawdown, cooldowns, kill switch) viven en
`protections.py` (ADR-0007) y solo afectan entradas.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from tradingbot.config.models import ExecutionConfig, RiskConfig
from tradingbot.domain.enums import ExitReason, Side, SignalAction
from tradingbot.domain.money import BPS_DENOMINATOR, ONE, ZERO
from tradingbot.domain.orders import OrderIntent, Signal, make_client_order_id
from tradingbot.domain.pair import Pair
from tradingbot.domain.positions import Position
from tradingbot.exchange.binance import MarketInfo
from tradingbot.risk.protections import Protections
from tradingbot.risk.sizing import ReasonCode, sellable_qty, size_by_risk


@dataclass(frozen=True, slots=True)
class PortfolioView:
    """Lo que el riesgo necesita saber del portfolio al evaluar un `Bar`."""

    equity: Decimal
    cash_available: Decimal  # cash libre menos lo reservado por compras pendientes
    positions: Mapping[Pair, Position]
    marks: Mapping[Pair, Decimal]  # close del bar por par
    pending_pairs: frozenset[Pair] = frozenset()
    pending_notional: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class Rejection:
    signal: Signal
    reason: ReasonCode
    detail: str = ""


@dataclass(frozen=True, slots=True)
class RiskDecision:
    intents: tuple[OrderIntent, ...] = ()
    rejections: tuple[Rejection, ...] = ()


@dataclass(frozen=True, slots=True)
class ExitDecision:
    intent: OrderIntent | None
    dust: Decimal = ZERO
    reason: ReasonCode | None = None
    detail: str = ""


@dataclass(slots=True)
class RiskManager:
    risk: RiskConfig
    execution: ExecutionConfig
    markets: Mapping[Pair, MarketInfo]
    strategy_name: str
    auto_resume: bool = True  # backtest: el circuit breaker reanuda solo; paper/live exige resume()
    _cost_factor: Decimal = field(init=False)
    protections: Protections = field(init=False)

    def __post_init__(self) -> None:
        self.protections = Protections(self.risk, auto_resume=self.auto_resume)
        factor = ONE + self.execution.slippage_bps / BPS_DENOMINATOR
        if self.execution.pay_with_bnb:
            factor *= ONE + self.execution.bnb_fee_rate
        self._cost_factor = factor

    @property
    def buy_cost_factor(self) -> Decimal:
        """Cash necesario por unidad de notional comprado (slippage y fee en quote si aplica)."""
        return self._cost_factor

    # ------------------------------------------------------------- entradas

    def evaluate_entries(
        self, signals: Sequence[Signal], view: PortfolioView, ts: int
    ) -> RiskDecision:
        """Convierte señales `ENTER_LONG` en intents, con ranking y límites de portfolio."""
        entries = [s for s in signals if s.action is SignalAction.ENTER_LONG]
        entries.sort(
            key=lambda s: (
                -(s.strength if s.strength is not None else float("-inf")),
                s.pair.symbol,
            )
        )

        # Un par con salida pendiente ya cuenta como posición; solo las compras pendientes
        # ocupan slots adicionales.
        pending_new = {p for p in view.pending_pairs if p not in view.positions}
        slots = self.risk.max_positions - len(view.positions) - len(pending_new)
        exposure_cap = view.equity * self.risk.max_exposure_pct
        exposure_used = view.pending_notional + sum(
            (p.qty * view.marks[p.pair] for p in view.positions.values() if p.pair in view.marks),
            ZERO,
        )
        cash_running = view.cash_available
        halt = self.protections.global_block()
        intents: list[OrderIntent] = []
        rejections: list[Rejection] = []

        for signal in entries:
            pair = signal.pair
            if pair in view.positions:
                rejections.append(Rejection(signal, ReasonCode.ALREADY_IN_POSITION))
                continue
            if pair in view.pending_pairs or any(i.pair == pair for i in intents):
                rejections.append(Rejection(signal, ReasonCode.PENDING_ORDER))
                continue
            block = halt or self.protections.pair_block(pair)
            if block is not None:
                rejections.append(Rejection(signal, block.reason, block.detail))
                continue
            if slots <= 0:
                rejections.append(
                    Rejection(signal, ReasonCode.MAX_POSITIONS, f"máx. {self.risk.max_positions}")
                )
                continue
            market = self.markets.get(pair)
            price = view.marks.get(pair)
            if market is None or price is None or signal.stop_price is None:
                rejections.append(
                    Rejection(signal, ReasonCode.INVALID_STOP, "sin mercado, precio o stop")
                )
                continue
            sizing = size_by_risk(
                equity=view.equity,
                cash_available=cash_running,
                price=price,
                stop=signal.stop_price,
                risk_per_trade=self.risk.risk_per_trade,
                max_position_pct=self.risk.max_position_pct,
                cost_factor=self._cost_factor,
                market=market,
            )
            if sizing.qty is None or sizing.reason is not None:
                rejections.append(
                    Rejection(signal, sizing.reason or ReasonCode.NO_CASH, sizing.detail)
                )
                continue
            if exposure_used + sizing.notional > exposure_cap:
                rejections.append(
                    Rejection(
                        signal,
                        ReasonCode.EXPOSURE_LIMIT,
                        f"exposición {exposure_used + sizing.notional} > {exposure_cap}",
                    )
                )
                continue
            intents.append(
                OrderIntent(
                    client_order_id=make_client_order_id(
                        self.strategy_name, pair, signal.open_time, Side.BUY
                    ),
                    strategy=self.strategy_name,
                    pair=pair,
                    side=Side.BUY,
                    qty=sizing.qty,
                    decision_price=price,
                    stop_price=signal.stop_price,
                    signal_ts=ts,
                    decision_ts=ts,
                    note=signal.note,
                )
            )
            slots -= 1
            exposure_used += sizing.notional
            cash_running -= sizing.notional * self._cost_factor
        return RiskDecision(intents=tuple(intents), rejections=tuple(rejections))

    # ------------------------------------------------------------- salidas

    def exit_intent(
        self,
        position: Position,
        exit_reason: ExitReason,
        decision_price: Decimal,
        ts: int,
        open_time: int,
    ) -> ExitDecision:
        """Intent de venta de toda la posición.

        Nunca bloquea: `intent=None` solo cuando el exchange no aceptaría la orden (cantidad
        vendible bajo `minQty` o notional bajo `minNotional`) y la posición queda `STUCK`.
        """
        market = self.markets[position.pair]
        qty, dust = sellable_qty(position.qty, market)
        if qty <= ZERO or qty < market.min_qty:
            return ExitDecision(None, dust, ReasonCode.MIN_QTY, f"qty vendible {qty}")
        if qty * decision_price < market.min_notional:
            return ExitDecision(
                None,
                dust,
                ReasonCode.MIN_NOTIONAL,
                f"notional {qty * decision_price} < {market.min_notional}",
            )
        intent = OrderIntent(
            client_order_id=make_client_order_id(
                self.strategy_name, position.pair, open_time, Side.SELL, exit_reason
            ),
            strategy=self.strategy_name,
            pair=position.pair,
            side=Side.SELL,
            qty=qty,
            decision_price=decision_price,
            signal_ts=ts,
            decision_ts=ts,
            exit_reason=exit_reason,
        )
        return ExitDecision(intent, dust)
