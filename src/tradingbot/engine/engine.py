"""`Engine`: el único loop de decisión (ADR-0002), idéntico en backtest, paper y live.

Por cada `Bar` cerrado, en este orden:
1. Fills de órdenes pendientes al open (`Broker.on_bar_open`); una compra sin cash se rechaza.
2. Stops en reposo con el rango de la vela (`Broker.on_bar`).
3. Mark-to-market al close y snapshot de equity.
4. `Strategy.on_candle` por par (orden alfabético).
5. Salidas: kill switch con `flatten` (todas las posiciones), reintento de las `STUCK`, señales
   `EXIT_LONG` (nunca bloqueadas) → intents `PENDING`.
6. Entradas vía `RiskManager` (protecciones ADR-0007, ranking, sizing, límites) → `PENDING`.
7. Trailing: `Strategy.trailing_stop` → `PositionManager` (solo sube) → `Broker.set_stop`; si el
   nivel queda en o sobre el close, se vende a mercado al open siguiente (un stop por encima del
   último precio no existe en el exchange).
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from tradingbot.config.models import ExecutionConfig
from tradingbot.data.feeds import MarketFeed
from tradingbot.domain.candle import Bar
from tradingbot.domain.enums import ExitReason, Side, SignalAction
from tradingbot.domain.money import ZERO
from tradingbot.domain.orders import Fill, OrderIntent, Signal
from tradingbot.domain.pair import Pair
from tradingbot.domain.positions import PortfolioSnapshot, Position, Trade
from tradingbot.engine.position_manager import PositionManager
from tradingbot.engine.series import RollingSeries, SeriesProvider
from tradingbot.exchange.binance import MarketInfo
from tradingbot.execution.broker import Broker, BrokerEvent
from tradingbot.execution.simulated import INSUFFICIENT_FUNDS, SimulatedBroker
from tradingbot.persistence.store import EventRecord, TradeStore
from tradingbot.prediction.base import EntryFilter
from tradingbot.risk.manager import PortfolioView, RiskManager
from tradingbot.risk.protections import KillSwitch
from tradingbot.risk.sizing import ReasonCode
from tradingbot.strategy.base import Strategy, StrategyContext

log = logging.getLogger(__name__)


@dataclass(slots=True)
class EngineStats:
    bars: int = 0
    signals: Counter[str] = field(default_factory=Counter)
    rejections: Counter[str] = field(default_factory=Counter)
    fills: int = 0
    stuck_pairs: set[Pair] = field(default_factory=set)
    protections: Counter[str] = field(default_factory=Counter)


@dataclass(frozen=True, slots=True)
class EngineState:
    """Lo que el motor necesita para reanudar tras un reinicio (ADR-0011).

    Las posiciones viven en la tabla `positions` del store (fuente de verdad); el resto va al
    `state` clave/valor. `to_dict`/`from_dict` son JSON-friendly (Decimal como texto).
    """

    cash: Decimal
    dust: Mapping[str, Decimal]
    positions: tuple[Position, ...]
    marks: Mapping[Pair, Decimal]
    bar_index: int
    last_bar_open_time: int | None
    last_exit_bar: Mapping[Pair, int]
    protections: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cash": str(self.cash),
            "dust": {k: str(v) for k, v in self.dust.items()},
            "marks": {p.symbol: str(v) for p, v in self.marks.items()},
            "bar_index": self.bar_index,
            "last_bar_open_time": self.last_bar_open_time,
            "last_exit_bar": {p.symbol: b for p, b in self.last_exit_bar.items()},
            "protections": dict(self.protections),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], positions: Iterable[Position]) -> EngineState:
        return cls(
            cash=Decimal(str(data["cash"])),
            dust={k: Decimal(str(v)) for k, v in dict(data.get("dust", {})).items()},
            positions=tuple(positions),
            marks={Pair.parse(k): Decimal(str(v)) for k, v in dict(data.get("marks", {})).items()},
            bar_index=int(data.get("bar_index", -1)),
            last_bar_open_time=None
            if data.get("last_bar_open_time") is None
            else int(data["last_bar_open_time"]),
            last_exit_bar={
                Pair.parse(k): int(v) for k, v in dict(data.get("last_exit_bar", {})).items()
            },
            protections=dict(data.get("protections", {})),
        )


class EngineListener(Protocol):
    """Quien quiera enterarse de lo que el motor hizo, además del `TradeStore` (ADR-0012).

    Se llama dentro del ciclo (en paper, dentro de la transacción): el listener acumula y avisa
    después del commit. Sin listener (backtest) no cambia nada.
    """

    def on_event(self, event: EventRecord) -> None: ...

    def on_position_opened(self, position: Position, fill: Fill) -> None: ...

    def on_trade_closed(self, trade: Trade, fill: Fill) -> None: ...


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
        kill_switch: KillSwitch | None = None,
        restore: EngineState | None = None,
        listener: EngineListener | None = None,
        entry_filter: EntryFilter | None = None,
    ) -> None:
        if initial_cash <= ZERO:
            msg = f"initial_cash debe ser positivo, recibido {initial_cash}"
            raise ValueError(msg)
        self.listener = listener
        self.entry_filter = entry_filter
        self._filter_error = False
        self._strategy = strategy
        self._feed = feed
        self._series = series
        self._broker = broker
        self._risk = risk
        self._kill_switch = kill_switch
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
        self._blocked: dict[Pair, str] = {}  # último motivo de rechazo por par (dedupe)
        self._bar_index = -1
        self._last_snapshot: PortfolioSnapshot | None = None
        self._last_bar_open_time: int | None = None  # última vela terminada (persistida)
        self._current_bar_open_time: int | None = None  # vela en proceso o recién terminada
        if isinstance(broker, SimulatedBroker):
            broker.bind_cash(lambda: self.cash)
        # Filtro de mercado (ADR-0009): se siembra con el warmup del feed para llegar definido al
        # primer bar (1200 velas de 4h = los 200 cierres diarios de la EMA).
        market_filter = risk.protections.market_filter
        self._reference: Pair | None = None if market_filter is None else market_filter.pair
        if self._reference is not None:
            for warm in feed.warmup_bars():
                candle = warm.get(self._reference)
                if candle is not None:
                    risk.protections.on_reference_candle(candle)
        if restore is not None:
            self._restore(restore)

    # ------------------------------------------------------------- recuperación (ADR-0011)

    def _restore(self, state: EngineState) -> None:
        self.cash = state.cash
        self.dust = dict(state.dust)
        self._marks = dict(state.marks)
        self._bar_index = state.bar_index
        self._last_bar_open_time = state.last_bar_open_time
        self._last_exit_bar = dict(state.last_exit_bar)
        if state.protections:
            self._risk.protections.restore(state.protections)
        ts = 0 if state.last_bar_open_time is None else state.last_bar_open_time
        self._positions.restore(state.positions, ts)
        self.stats.stuck_pairs |= self._positions.unprotected

    def state(self) -> EngineState:
        """Foto serializable del motor al terminar el último `Bar` procesado."""
        positions = tuple(self._positions.positions[p] for p in sorted(self._positions.positions))
        return EngineState(
            cash=self.cash,
            dust=dict(self.dust),
            positions=positions,
            marks=dict(self._marks),
            bar_index=self._bar_index,
            last_bar_open_time=self._last_bar_open_time,
            last_exit_bar=dict(self._last_exit_bar),
            protections=self._risk.protections.to_state(),
        )

    def indicator_checkpoint(self) -> dict[str, Any]:
        return self._series.checkpoint() if isinstance(self._series, RollingSeries) else {}

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

    @property
    def risk(self) -> RiskManager:
        return self._risk

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

    def flatten(self, open_time: int, ts: int, pairs: Collection[Pair] | None = None) -> None:
        """Vende a mercado al open siguiente todas las posiciones (o solo `pairs`, las del bar)."""
        for pair in sorted(self._positions.positions):
            if pairs is None or pair in pairs:
                self._submit_exit(pair, ExitReason.FLATTEN, open_time, ts)

    def _record(self, event: EventRecord) -> None:
        """Persiste el evento y después avisa al listener (ADR-0012)."""
        self._store.record_event(event)
        if self.listener is not None:
            self._emit(self.listener.on_event, event)

    @staticmethod
    def _emit(callback: Callable[..., None], *args: Any) -> None:
        """El listener es observacional: si falla, se loguea y el ciclo sigue (I2 de la revisión).

        Corre dentro de la transacción del paper con el estado ya mutado; una excepción acá
        dejaría la memoria del motor y la DB desalineadas.
        """
        try:
            callback(*args)
        except Exception:
            log.exception("engine: el listener falló en %s; se ignora", callback.__name__)

    def _drain_protection_events(self) -> None:
        for event in self._risk.protections.pop_events():
            self.stats.protections[f"{event.kind}:{event.reason.value}"] += 1
            self._record(
                EventRecord(
                    ts=event.ts,
                    kind=event.kind,
                    pair=event.pair,
                    reason=event.reason.value,
                    payload={"detail": event.detail},
                )
            )

    # ------------------------------------------------------------- loop por bar

    def process_bar(self, bar: Bar) -> None:
        self._bar_index += 1
        self.stats.bars += 1
        self._current_bar_open_time = bar.open_time
        ts = bar.close_time
        self._risk.protections.on_bar(self._bar_index, ts)

        for event in self._broker.on_bar_open(bar):  # 1
            self._apply_event(event)
        for event in self._broker.on_bar(bar):  # 2
            self._apply_event(event)

        for candle in bar.iter_candles():  # 3
            self._marks[candle.pair] = candle.close
            self._positions.mark(candle.pair, candle.close)
        if self._reference is not None:
            reference = bar.get(self._reference)
            if reference is not None:
                self._risk.protections.on_reference_candle(reference)
        self._snapshot(ts)
        self._risk.protections.on_equity(ts, self.equity())
        if self._kill_switch is not None:
            self._risk.protections.set_kill_switch(self._kill_switch.poll())
            if self._kill_switch.consume_resume():
                self._risk.protections.resume()
        self._drain_protection_events()

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

        self._filter_error = False
        if self.entry_filter is not None:
            try:
                self.entry_filter.observe(contexts, ts + 1)
            except Exception:
                log.exception("predicciones no disponibles; se bloquean nuevas compras")
                self._filter_error = True

        if self._risk.protections.flatten_requested:  # 5: kill switch con flatten
            self.flatten(bar.open_time, ts, bar.pairs)
        for pair, reason in list(self._stuck_exits.items()):  # 5a: reintentar salidas trabadas
            if pair in bar.pairs:
                self._submit_exit(pair, reason, bar.open_time, ts)
        for pair, signal in signals.items():  # 5b: salidas por señal
            if signal.action is SignalAction.EXIT_LONG:
                self._submit_exit(
                    pair, signal.exit_reason or ExitReason.SIGNAL, signal.open_time, ts
                )

        if bar.replay:  # 6: reposición tras reinicio, sin entradas nuevas (ADR-0011)
            self._reject_replay_entries(list(signals.values()), ts)
        else:
            self._submit_entries(list(signals.values()), ts)

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
        # Al final: si el ciclo explota a mitad, la vela se re-procesa al reiniciar (ADR-0011).
        self._last_bar_open_time = bar.open_time

    # ------------------------------------------------------------- fills

    def apply_events(self, events: Iterable[BrokerEvent]) -> None:
        """Fills o rechazos que el broker produjo fuera del ciclo del `Bar` (paper: fill
        inmediato al open de la vela en formación, stops del `StopWatcher`). Mismo camino que
        los eventos de `on_bar_open`/`on_bar` (ADR-0011)."""
        for event in events:
            self._apply_event(event)

    def _apply_event(self, event: BrokerEvent) -> None:
        intent = event.order.intent
        self._store.save_order(event.order)
        if event.fill is None:
            self._pending_entries.pop(intent.client_order_id, None)
            self._pending_exits.pop(intent.pair, None)
            reason = (event.order.reject_reason or INSUFFICIENT_FUNDS).split(":")[0]
            self.stats.rejections[reason] += 1
            self._record(
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
            opened = self._positions.open_from_fill(intent, fill)
            if self.listener is not None:
                self._emit(self.listener.on_position_opened, opened, fill)
            return
        position = self._positions.get(fill.pair)
        if position is None:
            self._record(
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
        trade = self._positions.close_from_fill(fill, intent.exit_reason or ExitReason.SIGNAL)
        if self.listener is not None:
            self._emit(self.listener.on_trade_closed, trade, fill)
        exit_bar = self._bar_of(fill.fill_ts)
        self._risk.protections.on_trade_closed(trade, bar_index=exit_bar)
        self._drain_protection_events()
        self._pending_exits.pop(fill.pair, None)
        self._stuck_exits.pop(fill.pair, None)
        self._last_exit_bar[fill.pair] = exit_bar
        self.stats.stuck_pairs.discard(fill.pair)

    def _bar_of(self, ts: int) -> int:
        """Índice de la vela a la que pertenece `ts`.

        En backtest los fills llegan dentro del ciclo de su vela. En paper llegan fuera (fill
        inmediato al open de `t+1`, stop del watcher a mitad de `t+1`) con `_bar_index` todavía
        en `t`: se cuentan las velas que abrieron después de la actual para que `bars_since_exit`
        y los cooldowns den lo mismo que en backtest (ADR-0011).
        """
        if self._current_bar_open_time is None:
            return self._bar_index
        tf = self._feed.timeframe
        ahead = (tf.floor(ts) - self._current_bar_open_time) // tf.ms
        return self._bar_index + max(ahead, 0)

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
                self._record(
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
            self._blocked = {}  # sin señales: el próximo rechazo es una decisión nueva
            return
        if self.entry_filter is not None:
            accepted = []
            for signal in entries:
                try:
                    if self._filter_error:
                        raise ValueError("prediction_unavailable")
                    prediction_decision = self.entry_filter.evaluate(signal, ts + 1)
                    if prediction_decision.accepted:
                        accepted.append(signal)
                        continue
                    reason = prediction_decision.reason
                except Exception:
                    reason = "prediction_unavailable"
                self.stats.rejections[reason] += 1
                self._record(
                    EventRecord(ts=ts, kind="entry_rejected", pair=signal.pair, reason=reason)
                )
            entries = accepted
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
        blocked: dict[Pair, str] = {}
        for rejection in decision.rejections:
            self.stats.rejections[rejection.reason.value] += 1
            pair = rejection.signal.pair
            blocked[pair] = rejection.reason.value
            if self._blocked.get(pair) == rejection.reason.value:
                continue  # mismo motivo que la vela anterior: se cuenta, no se repite el evento
            self._record(
                EventRecord(
                    ts=ts,
                    kind="entry_rejected",
                    pair=pair,
                    reason=rejection.reason.value,
                    payload={"detail": rejection.detail},
                )
            )
        self._blocked = blocked
        for intent in decision.intents:
            order = self._broker.submit(intent, ts)
            self._store.save_order(order)
            self._pending_entries[intent.client_order_id] = intent

    def _reject_replay_entries(self, signals: list[Signal], ts: int) -> None:
        for signal in signals:
            if signal.action is not SignalAction.ENTER_LONG:
                continue
            self.stats.rejections[ReasonCode.REPLAY.value] += 1
            self._record(
                EventRecord(
                    ts=ts,
                    kind="entry_rejected",
                    pair=signal.pair,
                    reason=ReasonCode.REPLAY.value,
                    payload={"detail": "vela de reposición tras reinicio"},
                )
            )

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
