"""`Engine`: el único loop de decisión (ADR-0002), idéntico en backtest, paper y live.

Por cada `Bar` cerrado, en este orden:
1. Fills de órdenes pendientes al open (`Broker.on_bar_open`); una compra sin cash se rechaza.
2. Stops en reposo con el rango de la vela (`Broker.on_bar`).
3. Mark-to-market al close y snapshot de equity.
4. `Strategy.on_candle` por par (orden alfabético).
5. Salidas: reintento de las `STUCK`, señales `EXIT_LONG` (nunca bloqueadas) → intents `PENDING`.
6. Entradas vía `RiskManager` (ranking, sizing, límites) → intents `PENDING`.
7. Trailing: `Strategy.trailing_stop` → `PositionManager` (solo sube) → `Broker.set_stop`; si el
   nivel queda en o sobre el close, se vende a mercado al open siguiente (un stop por encima del
   último precio no existe en el exchange).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from tradingbot.config.models import ExecutionConfig
from tradingbot.data.feeds import MarketFeed
from tradingbot.domain.candle import Bar
from tradingbot.domain.enums import ExitReason, Side, SignalAction
from tradingbot.domain.money import ZERO
from tradingbot.domain.orders import OrderIntent, Signal
from tradingbot.domain.pair import Pair
from tradingbot.domain.positions import PortfolioSnapshot
from tradingbot.engine.position_manager import PositionManager
from tradingbot.engine.series import SeriesProvider
from tradingbot.exchange.binance import MarketInfo
from tradingbot.execution.broker import Broker, BrokerEvent
from tradingbot.execution.simulated import INSUFFICIENT_FUNDS, SimulatedBroker
from tradingbot.persistence.store import EventRecord, TradeStore
from tradingbot.risk.manager import PortfolioView, RiskManager
from tradingbot.strategy.base import Strategy, StrategyContext


@dataclass(slots=True)
class EngineStats:
    bars: int = 0
    signals: Counter[str] = field(default_factory=Counter)
    rejections: Counter[str] = field(default_factory=Counter)
    fills: int = 0
    stuck_pairs: set[Pair] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class EngineResult:
    cash: Decimal
    dust: Mapping[str, Decimal]
    final_snapshot: PortfolioSnapshot | None
    stats: EngineStats
    store: TradeStore


class Engine:
    def __init__(
        self,
        *,
        strategy: Strategy,
        feed: MarketFeed,
        series: SeriesProvider,
        broker: Broker,
        risk: RiskManager,
        store: TradeStore,
        markets: Mapping[Pair, MarketInfo],
        execution: ExecutionConfig,
        initial_cash: Decimal,
    ) -> None:
        if initial_cash <= ZERO:
            msg = f"initial_cash debe ser positivo, recibido {initial_cash}"
            raise ValueError(msg)
        self._strategy = strategy
        self._feed = feed
        self._series = series
        self._broker = broker
        self._risk = risk
        self._store = store
        self._execution = execution
        self._positions = PositionManager(broker, store, markets)
        self.cash = initial_cash
        self.dust: dict[str, Decimal] = {}
        self.stats = EngineStats()
        self._marks: dict[Pair, Decimal] = {}
        self._pending_entries: dict[str, OrderIntent] = {}
        self._pending_exits: dict[Pair, OrderIntent] = {}
        self._stuck_exits: dict[Pair, ExitReason] = {}
        self._last_exit_bar: dict[Pair, int] = {}
        self._bar_index = -1
        self._last_snapshot: PortfolioSnapshot | None = None
        if isinstance(broker, SimulatedBroker):
            broker.bind_cash(lambda: self.cash)

    # ------------------------------------------------------------- API

    async def run(self) -> EngineResult:
        async for bar in self._feed:
            self.process_bar(bar)
        return EngineResult(
            cash=self.cash,
            dust=dict(self.dust),
            final_snapshot=self._last_snapshot,
            stats=self.stats,
            store=self._store,
        )

    @property
    def positions(self) -> PositionManager:
        return self._positions

    def equity(self) -> Decimal:
        value = sum(
            (
                p.qty * self._marks[p.pair]
                for p in self._positions.positions.values()
                if p.pair in self._marks
            ),
            ZERO,
        )
        return self.cash + value

    # ------------------------------------------------------------- loop por bar

    def process_bar(self, bar: Bar) -> None:
        self._bar_index += 1
        self.stats.bars += 1
        ts = bar.close_time

        for event in self._broker.on_bar_open(bar):  # 1
            self._apply_event(event)
        for event in self._broker.on_bar(bar):  # 2
            self._apply_event(event)

        for candle in bar.iter_candles():  # 3
            self._marks[candle.pair] = candle.close
            self._positions.mark(candle.pair, candle.close)
        self._snapshot(ts)

        signals: dict[Pair, Signal] = {}  # 4
        contexts: dict[Pair, StrategyContext] = {}
        for pair in bar.pairs:
            series = self._series.at(pair, bar)
            if series is None:
                continue
            last_exit = self._last_exit_bar.get(pair)
            ctx = StrategyContext(
                ohlcv=series.ohlcv,
                indicators=series.indicators,
                index=series.index,
                position=self._positions.get(pair),
                equity=self.equity(),
                cash=self.cash,
                bars_since_exit=None if last_exit is None else self._bar_index - last_exit,
            )
            signal = self._strategy.on_candle(ctx)
            self.stats.signals[signal.action.value] += 1
            signals[pair] = signal
            contexts[pair] = ctx

        for pair, reason in list(self._stuck_exits.items()):  # 5a: reintentar salidas trabadas
            if pair in bar.pairs:
                self._submit_exit(pair, reason, bar.open_time, ts)
        for pair, signal in signals.items():  # 5b: salidas por señal
            if signal.action is SignalAction.EXIT_LONG:
                self._submit_exit(
                    pair, signal.exit_reason or ExitReason.SIGNAL, signal.open_time, ts
                )

        self._submit_entries(list(signals.values()), ts)  # 6

        for pair, ctx in contexts.items():  # 7
            if pair in self._pending_exits or self._positions.get(pair) is None:
                continue
            level = self._strategy.trailing_stop(ctx)
            if level is None:
                continue
            if level >= ctx.candle.close:
                # Un stop en o sobre el último precio no existe en el exchange: salida a mercado.
                self._submit_exit(pair, ExitReason.TRAILING, ctx.open_time, ts)
                continue
            self._positions.update_trailing(pair, level, ts)
        self.stats.stuck_pairs |= self._positions.unprotected

    # ------------------------------------------------------------- fills

    def _apply_event(self, event: BrokerEvent) -> None:
        intent = event.order.intent
        self._store.save_order(event.order)
        if event.fill is None:
            self._pending_entries.pop(intent.client_order_id, None)
            self._pending_exits.pop(intent.pair, None)
            reason = (event.order.reject_reason or INSUFFICIENT_FUNDS).split(":")[0]
            self.stats.rejections[reason] += 1
            self._store.record_event(
                EventRecord(
                    ts=event.order.updated_ts,
                    kind="entry_rejected" if intent.side is Side.BUY else "exit_rejected",
                    pair=intent.pair,
                    reason=reason,
                    payload={"detail": event.order.reject_reason or ""},
                )
            )
            return
        fill = event.fill
        self.stats.fills += 1
        self._store.save_fill(fill)
        if fill.side is Side.BUY:
            cost = fill.notional
            if fill.fee_asset == fill.pair.quote:
                cost += fill.fee_amount
            self.cash -= cost
            self._pending_entries.pop(intent.client_order_id, None)
            self._positions.open_from_fill(intent, fill)
            return
        position = self._positions.get(fill.pair)
        if position is None:
            self._store.record_event(
                EventRecord(
                    ts=fill.fill_ts,
                    kind="orphan_sell_fill",
                    pair=fill.pair,
                    reason=intent.client_order_id,
                )
            )
            return
        leftover = position.qty - fill.qty
        if leftover > ZERO:
            self.dust[fill.pair.base] = self.dust.get(fill.pair.base, ZERO) + leftover
        self.cash += fill.net_quote_amount
        self._positions.close_from_fill(fill, intent.exit_reason or ExitReason.SIGNAL)
        self._pending_exits.pop(fill.pair, None)
        self._stuck_exits.pop(fill.pair, None)
        self._last_exit_bar[fill.pair] = self._bar_index
        self.stats.stuck_pairs.discard(fill.pair)

    # ------------------------------------------------------------- decisiones

    def _submit_exit(self, pair: Pair, reason: ExitReason, open_time: int, ts: int) -> None:
        position = self._positions.get(pair)
        if position is None:
            self._stuck_exits.pop(pair, None)
            return
        if pair in self._pending_exits:
            return
        price = self._marks[pair]
        decision = self._risk.exit_intent(position, reason, price, ts, open_time)
        if decision.intent is None:
            if pair not in self._stuck_exits:
                self._store.record_event(
                    EventRecord(
                        ts=ts,
                        kind="exit_stuck",
                        pair=pair,
                        reason=str(decision.reason),
                        payload={"detail": decision.detail},
                    )
                )
            self._stuck_exits[pair] = reason
            self.stats.stuck_pairs.add(pair)
            return
        self._stuck_exits.pop(pair, None)
        self._broker.cancel_stop(pair)  # la venta a mercado reemplaza al stop en reposo
        order = self._broker.submit(decision.intent, ts)
        self._store.save_order(order)
        self._pending_exits[pair] = decision.intent

    def _submit_entries(self, signals: list[Signal], ts: int) -> None:
        entries = [s for s in signals if s.action is SignalAction.ENTER_LONG]
        if not entries:
            return
        reserved = sum(
            (
                i.expected_notional * self._risk.buy_cost_factor
                for i in self._pending_entries.values()
            ),
            ZERO,
        )
        view = PortfolioView(
            equity=self.equity(),
            cash_available=self.cash - reserved,
            positions=self._positions.positions,
            marks=dict(self._marks),
            pending_pairs=frozenset(i.pair for i in self._pending_entries.values())
            | frozenset(self._pending_exits),
            pending_notional=sum(
                (i.expected_notional for i in self._pending_entries.values()), ZERO
            ),
        )
        decision = self._risk.evaluate_entries(entries, view, ts)
        for rejection in decision.rejections:
            self.stats.rejections[rejection.reason.value] += 1
            self._store.record_event(
                EventRecord(
                    ts=ts,
                    kind="entry_rejected",
                    pair=rejection.signal.pair,
                    reason=rejection.reason.value,
                    payload={"detail": rejection.detail},
                )
            )
        for intent in decision.intents:
            order = self._broker.submit(intent, ts)
            self._store.save_order(order)
            self._pending_entries[intent.client_order_id] = intent

    # ------------------------------------------------------------- snapshot

    def _snapshot(self, ts: int) -> None:
        positions = tuple(self._positions.positions[p] for p in sorted(self._positions.positions))
        snapshot = PortfolioSnapshot(
            ts=ts,
            cash=self.cash,
            positions=positions,
            marks=dict(self._marks),
            dust=dict(self.dust),
        )
        self._store.snapshot_equity(snapshot)
        self._last_snapshot = snapshot
