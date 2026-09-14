"""Sesión de paper trading (ADR-0011).

Arma `LiveFeed` → `Engine` → `PaperBroker` → `SqliteStore` con la config de modo `paper`, reanuda
desde la DB si hay estado, y por cada `Bar` cerrado: procesa, llena las órdenes al open de la vela
en formación, revisa stops, persiste el estado del motor y escribe `logs/status.json`. El
`StopWatcher` corre como tarea aparte entre cierres. `SIGTERM`/`SIGINT` terminan el ciclo en curso
y salen con el estado guardado.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from tradingbot import __version__
from tradingbot.backtest.runner import load_markets_for
from tradingbot.config.models import Mode
from tradingbot.config.settings import BotConfig
from tradingbot.data.live_feed import FeedEvent, LiveFeed
from tradingbot.domain.candle import Candle
from tradingbot.domain.enums import OrderStatus
from tradingbot.domain.errors import ConfigError, ExchangeError
from tradingbot.domain.money import ZERO
from tradingbot.domain.pair import Pair
from tradingbot.domain.timeframe import Timeframe
from tradingbot.engine.engine import Engine, EngineState
from tradingbot.engine.series import RollingSeries
from tradingbot.exchange.binance import MarketInfo
from tradingbot.execution.broker import BrokerEvent
from tradingbot.execution.paper import PaperBroker, StopWatcher
from tradingbot.observability.status import StatusWriter
from tradingbot.persistence.sqlite import SqliteStore
from tradingbot.persistence.store import EventRecord
from tradingbot.risk.manager import RiskManager
from tradingbot.risk.protections import FileKillSwitch
from tradingbot.strategy.base import Strategy
from tradingbot.strategy.registry import build_strategy, effective_warmup

log = logging.getLogger(__name__)

ENGINE_STATE_KEY = "engine"
SESSION_STATE_KEY = "session"
PENDING_DROPPED = "pending_dropped"
AsyncSleep = Callable[[float], Awaitable[None]]


class PaperExchange(Protocol):
    """Reloj, velas, último precio y mercados: lo que `BinanceExchange` ya provee."""

    def now_ms(self) -> int: ...

    def fetch_ohlcv_page(
        self, pair: Pair, timeframe: Timeframe, since_ms: int, limit: int = 1000
    ) -> list[Candle]: ...

    def fetch_last_price(self, pair: Pair) -> Decimal: ...

    def load_markets(self, reload: bool = False) -> dict[Pair, MarketInfo]: ...


def _iso(ts_ms: int | None) -> str:
    if ts_ms is None:
        return "-"
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")


def _markets_for(config: BotConfig, exchange: PaperExchange) -> dict[Pair, MarketInfo]:
    pairs = list(config.strategy.pairs)
    try:
        markets = exchange.load_markets()
    except ExchangeError as exc:
        log.warning("paper: sin mercados del exchange (%s); se usa el snapshot", exc)
        return load_markets_for(pairs, None)
    return load_markets_for(pairs, markets)


@dataclass
class PaperSession:
    config: BotConfig
    strategy: Strategy
    exchange: PaperExchange
    store: SqliteStore
    feed: LiveFeed
    broker: PaperBroker
    engine: Engine
    watcher: StopWatcher
    kill_switch: FileKillSwitch
    status: StatusWriter
    restored: bool
    recent: deque[str] = field(default_factory=lambda: deque(maxlen=20))
    bars_processed: int = 0
    _stopping: bool = field(default=False, init=False)

    # ------------------------------------------------------------- eventos

    def note(self, text: str) -> None:
        self.recent.append(f"{_iso(self.exchange.now_ms())} {text}")
        log.info(text)

    def on_feed_event(self, event: FeedEvent) -> None:
        self.store.record_event(
            EventRecord(
                ts=event.ts, kind=event.kind, pair=event.pair, reason=event.detail[:80], payload={}
            )
        )
        self.note(f"{event.kind} {'' if event.pair is None else event.pair.symbol} {event.detail}")

    def on_broker_events(self, events: list[BrokerEvent]) -> None:
        self.engine.apply_events(events)
        for event in events:
            intent = event.order.intent
            if event.fill is None:
                self.note(f"orden {intent.client_order_id} rechazada: {event.order.reject_reason}")
            else:
                self.note(
                    f"fill {intent.side.value} {intent.pair.symbol} {event.fill.qty} @ "
                    f"{event.fill.price} "
                    f"({intent.exit_reason.value if intent.exit_reason else 'entrada'})"
                )
        self.persist()

    # ------------------------------------------------------------- persistencia y status

    def persist(self) -> None:
        self.store.save_state(ENGINE_STATE_KEY, self.engine.state().to_dict())
        self.store.save_state(
            SESSION_STATE_KEY,
            {"version": __version__, "saved_ts": self.exchange.now_ms(), "mode": self.config.mode},
        )

    def status_payload(self, phase: str) -> dict[str, Any]:
        state = self.engine.state()
        marks = state.marks
        positions = [
            {
                "pair": p.pair.symbol,
                "qty": str(p.qty),
                "entry_price": str(p.entry_price),
                "stop_price": str(p.stop_price),
                "mark": None if p.pair not in marks else str(marks[p.pair]),
                "unrealized_pnl": None
                if p.pair not in marks
                else str(p.unrealized_pnl(marks[p.pair])),
                "stop_published": self.broker.get_stop(p.pair) is not None,
            }
            for p in state.positions
        ]
        stats = self.engine.stats
        tf = self.config.strategy.timeframe
        last = state.last_bar_open_time
        return {
            "mode": self.config.mode.value,
            "phase": phase,
            "bot_version": __version__,
            "strategy": self.strategy.name,
            "params": self.strategy.params.model_dump(mode="json"),
            "timeframe": tf.value,
            "timeframe_ms": tf.ms,
            "pairs": [p.symbol for p in self.config.strategy.pairs],
            "restored_from_db": self.restored,
            "last_bar_open_time": last,
            "last_bar_utc": _iso(last),
            "next_close_utc": _iso(None if last is None else last + 2 * tf.ms),
            "cash": str(state.cash),
            "equity": str(self.engine.equity()),
            "dust": {k: str(v) for k, v in state.dust.items()},
            "positions": positions,
            "pending_orders": [o.client_order_id for o in self.broker.pending_orders()],
            "protections": self.engine.risk.protections.status(),
            "kill_switch_file": str(self.kill_switch.path),
            "kill_switch_active": self.kill_switch.poll().active,
            "stats": {
                "bars": stats.bars,
                "fills": stats.fills,
                "signals": dict(stats.signals),
                "rejections": dict(stats.rejections),
                "protections": dict(stats.protections),
                "stuck_pairs": sorted(p.symbol for p in stats.stuck_pairs),
                "price_errors": self.broker.price_errors,
                "watcher_ticks": self.watcher.ticks,
            },
            "recent_events": list(self.recent),
            "db": {"path": str(self.store.path), "counts": self.store.counts()},
        }

    def write_status(self, phase: str = "corriendo") -> None:
        try:
            self.status.write(self.status_payload(phase), heartbeat_ts=self.exchange.now_ms())
        except OSError as exc:  # el status nunca tumba el bot
            log.warning("paper: no se pudo escribir status.json (%s)", exc)

    # ------------------------------------------------------------- ciclo

    def request_stop(self) -> None:
        if not self._stopping:
            self._stopping = True
            self.note("parada solicitada: se termina el ciclo en curso y se guarda el estado")
        self.feed.stop()
        self.watcher.stop()

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.request_stop)
            except (NotImplementedError, RuntimeError):  # Windows / hilos secundarios
                with contextlib.suppress(ValueError):
                    signal.signal(sig, lambda *_args: self.request_stop())

    def process(self, bar: Any) -> None:
        """Un cierre: motor, fills inmediatos, stops, persistencia y status."""
        tf = self.config.strategy.timeframe.ms
        self.engine.process_bar(bar)
        self.engine.apply_events(self.broker.fill_pending(bar.open_time + tf))
        self.watcher.tick()
        self.bars_processed += 1
        self.note(
            f"vela {_iso(bar.open_time)}{' (reposición)' if bar.replay else ''}: "
            f"equity {self.engine.equity():.2f}, posiciones {len(self.engine.positions)}"
        )
        self.persist()
        self.write_status()

    async def run(self, *, max_bars: int | None = None, install_signals: bool = True) -> int:
        """Corre hasta `request_stop()` (o `max_bars`). Devuelve la cantidad de velas procesadas."""
        if install_signals:
            self._install_signal_handlers()
        self.note(
            f"paper {self.strategy.name} {self.config.strategy.timeframe.value} "
            f"{', '.join(p.symbol for p in self.config.strategy.pairs)}: "
            f"{'reanudado desde la DB' if self.restored else 'arranque limpio'}, "
            f"{self.feed.replay_pending} velas de reposición"
        )
        self.write_status("arranque")
        watcher_task = asyncio.create_task(self.watcher.run())
        try:
            async for bar in self.feed:
                self.process(bar)
                if max_bars is not None and self.bars_processed >= max_bars:
                    self.request_stop()
                    break
        finally:
            self.watcher.stop()
            watcher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await watcher_task
            self.persist()
            self.write_status("detenido")
            self.store.close()
        return self.bars_processed


def _drop_pending_orders(store: SqliteStore, now_ms: int) -> int:
    """Órdenes `PENDING` de la sesión anterior: en paper no hubo exchange que las llenara."""
    dropped = 0
    for order in store.orders():
        if order.status is not OrderStatus.PENDING:
            continue
        store.save_order(
            order.with_status(
                OrderStatus.CANCELED, ts=now_ms, reason=f"{PENDING_DROPPED}: reinicio del proceso"
            )
        )
        store.record_event(
            EventRecord(
                ts=now_ms,
                kind=PENDING_DROPPED,
                pair=order.intent.pair,
                reason=order.client_order_id,
                payload={"side": order.intent.side.value},
            )
        )
        dropped += 1
    return dropped


def build_paper_session(
    config: BotConfig,
    exchange: PaperExchange,
    *,
    store: SqliteStore | None = None,
    status_path: Path | None = None,
    sleep: AsyncSleep = asyncio.sleep,
) -> PaperSession:
    if config.mode is not Mode.PAPER:
        msg = f"la sesión de paper exige `mode: paper` en la config (recibido {config.mode})"
        raise ConfigError(msg)
    strategy = build_strategy(config.strategy)
    warmup = effective_warmup(config.strategy, strategy)
    timeframe = config.strategy.timeframe
    pairs = list(config.strategy.pairs)
    markets = _markets_for(config, exchange)
    store = store if store is not None else SqliteStore(config.db_path)
    now = exchange.now_ms()

    restore: EngineState | None = None
    raw_state = store.load_state(ENGINE_STATE_KEY)
    if raw_state is not None:
        restore = EngineState.from_dict(raw_state, store.load_open_positions())
    dropped = _drop_pending_orders(store, now)

    # El feed y el watcher se construyen antes que la sesión: sus eventos se enrutan a través de
    # `holder` (vacío hasta que la sesión exista; lo del bootstrap se guarda y se entrega después).
    holder: list[PaperSession] = []
    early_events: list[FeedEvent] = []

    def on_feed_event(event: FeedEvent) -> None:
        if holder:
            holder[0].on_feed_event(event)
        else:
            early_events.append(event)

    def on_broker_events(events: list[BrokerEvent]) -> None:
        holder[0].on_broker_events(events)

    feed = LiveFeed(
        exchange,
        pairs,
        timeframe,
        warmup,
        resume_from=None if restore is None else restore.last_bar_open_time,
        sleep=sleep,
        on_event=on_feed_event,
    )
    feed.bootstrap()
    series = RollingSeries(
        strategy, {pair: feed.warmup_candles(pair) for pair in pairs}, window=warmup + 1
    )
    broker = PaperBroker(config.execution, markets, exchange, timeframe)
    risk = RiskManager(config.risk, config.execution, markets, strategy.name, auto_resume=False)
    kill_switch = FileKillSwitch(config.risk.kill_switch_file)
    initial_cash = config.backtest.initial_cash
    if restore is not None and restore.cash > ZERO:
        initial_cash = restore.cash
    engine = Engine(
        strategy=strategy,
        feed=feed,
        series=series,
        broker=broker,
        risk=risk,
        store=store,
        markets=markets,
        execution=config.execution,
        initial_cash=initial_cash,
        kill_switch=kill_switch,
        restore=restore,
    )
    status = StatusWriter(
        status_path if status_path is not None else config.persistence.logs_dir / "status.json"
    )
    session = PaperSession(
        config=config,
        strategy=strategy,
        exchange=exchange,
        store=store,
        feed=feed,
        broker=broker,
        engine=engine,
        watcher=StopWatcher(
            broker, config.execution.stop_watch_interval_s, on_broker_events, sleep=sleep
        ),
        kill_switch=kill_switch,
        status=status,
        restored=restore is not None,
    )
    holder.append(session)
    for event in early_events:
        session.on_feed_event(event)
    if dropped:
        session.note(f"{dropped} orden(es) pendientes de la sesión anterior canceladas")
    return session
