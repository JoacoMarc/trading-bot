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
import os
import signal
from collections import deque
from collections.abc import Awaitable, Callable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from tradingbot import __version__
from tradingbot.backtest.runner import load_markets_for
from tradingbot.config.models import Mode
from tradingbot.config.settings import BotConfig
from tradingbot.data.live_feed import FEED_RETRY, FeedEvent, LiveFeed
from tradingbot.domain.candle import Bar, Candle
from tradingbot.domain.enums import ExitReason, OrderStatus
from tradingbot.domain.errors import ConfigError, ExchangeError
from tradingbot.domain.money import ZERO
from tradingbot.domain.orders import Fill
from tradingbot.domain.pair import Pair
from tradingbot.domain.positions import PortfolioSnapshot, Position, Trade
from tradingbot.domain.timeframe import Timeframe
from tradingbot.engine.engine import Engine, EngineState
from tradingbot.engine.series import RollingSeries
from tradingbot.exchange.binance import MarketInfo
from tradingbot.execution.broker import BrokerEvent
from tradingbot.execution.paper import PaperBroker, StopWatcher
from tradingbot.notify import texts
from tradingbot.notify.base import (
    Category,
    Level,
    LogNotifier,
    Notification,
    Notifier,
    resolve_level,
)
from tradingbot.notify.commands import CommandService
from tradingbot.observability.status import StatusWriter
from tradingbot.persistence.sqlite import SqliteStore
from tradingbot.persistence.store import EventRecord
from tradingbot.risk.manager import RiskManager
from tradingbot.risk.protections import FileKillSwitch
from tradingbot.risk.sizing import ReasonCode
from tradingbot.strategy.base import Strategy
from tradingbot.strategy.registry import build_strategy, effective_warmup

log = logging.getLogger(__name__)

ENGINE_STATE_KEY = "engine"
SESSION_STATE_KEY = "session"
PENDING_DROPPED = "pending_dropped"
AsyncSleep = Callable[[float], Awaitable[None]]
NOTIFIER_STOP_TIMEOUT_S = 15.0
STALE_ALERT_TIMEOUT_S = 5.0
DAILY_CHECK_S = 60.0


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
    _sleep: AsyncSleep = field(default=asyncio.sleep, repr=False)
    notifier: Notifier = field(default_factory=LogNotifier)
    daily_summary: bool = True
    recent: deque[str] = field(default_factory=lambda: deque(maxlen=20))
    bars_processed: int = 0
    watchdog_grace_ms: int = 300_000
    watchdog_interval_s: float = 60.0
    on_stale: Callable[[], None] | None = None  # default: salir con 1 (Docker reinicia)
    _stopping: bool = field(default=False, init=False)
    _last_cycle_ts: int = field(default=0, init=False)
    _next_open: int | None = field(default=None, init=False)
    _pending_notes: list[Notification] = field(default_factory=list, init=False, repr=False)
    _last_daily_key: int | None = field(default=None, init=False)
    _cycle_failed: bool = field(default=False, init=False)
    _pending_operations: list[tuple[Position | Trade, Fill, Decimal]] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._last_cycle_ts = self.exchange.now_ms()
        self.engine.listener = self
        self._tz = ZoneInfo(self.config.notify.timezone)
        self.commands = CommandService(
            self,
            timezone=self.config.notify.timezone,
            confirm_window_s=self.config.notify.confirm_window_s,
        )

    # ------------------------------------------------------------- eventos

    def note(self, text: str) -> None:
        self.recent.append(f"{_iso(self.exchange.now_ms())} {text}")
        log.info(text)

    @property
    def instance_name(self) -> str:
        return self.config.notify.instance_name or self.strategy.name

    @property
    def notification_prefix(self) -> str:
        return f"[{self.config.mode.value.upper()} | {self.instance_name}] "

    def _queue_note(
        self,
        category: Category,
        text: str,
        ts: int,
        pair: Pair | None = None,
        delivery_id: str | None = None,
    ) -> None:
        """Aviso que espera al commit del ciclo (ADR-0012). `ts` es el del fill o del evento."""
        self._pending_notes.append(
            Notification(ts=ts, category=category, text=text, pair=pair, delivery_id=delivery_id)
        )

    def flush_notifications(self) -> None:
        notes, self._pending_notes = self._pending_notes, []
        for note in notes:
            if not (self.config.notify.telegram_enabled and note.delivery_id is not None):
                self.notifier.notify(note)

    @contextlib.contextmanager
    def _cycle(self) -> Iterator[None]:
        """Transacción del ciclo: si falla, las notas acumuladas se descartan (I1).

        Lo que no quedó en la DB no se avisa; la vela se re-procesa al reiniciar y avisa entonces.
        """
        try:
            with self.store.transaction():
                yield
                if self.config.notify.telegram_enabled:
                    # Formatear fuera del listener observacional: una falla debe hacer rollback.
                    for record, fill, cash in self._pending_operations:
                        if isinstance(record, Position):
                            category = Category.ENTRY
                            text = texts.entry_text(fill, record, self._tz)
                        else:
                            by_stop = record.exit_reason in (ExitReason.STOP, ExitReason.TRAILING)
                            category = Category.STOP if by_stop else Category.EXIT
                            text = texts.exit_text(record, fill, cash, self._tz)
                        self._queue_note(
                            category,
                            text,
                            fill.fill_ts,
                            fill.pair,
                            f"{self.instance_name}:{fill.client_order_id}:{category.value}",
                        )
                    for note in self._pending_notes:
                        level = resolve_level(self.config.notify.events, note.category)
                        if note.delivery_id is not None and level is not Level.OFF:
                            self.store.enqueue_notification(
                                note.delivery_id,
                                self.notification_prefix + note.text,
                                level is Level.SILENT,
                                note.ts,
                            )
            self._pending_operations.clear()
        except BaseException:
            self._pending_notes.clear()
            self._pending_operations.clear()
            self._cycle_failed = True
            raise

    def announce(self, category: Category, text: str, pair: Pair | None = None) -> None:
        """Aviso inmediato (fuera de una transacción) que además queda en `recent`."""
        self.note(text)
        self.notifier.notify(
            Notification(ts=self.exchange.now_ms(), category=category, text=text, pair=pair)
        )

    # EngineListener (ADR-0012): se llama dentro de la transacción; se avisa tras el commit.

    def on_event(self, event: EventRecord) -> None:
        if event.kind.startswith("protection_"):
            category, text = Category.PROTECTION, texts.protection_text(event, self._tz)
        elif event.kind == "exit_stuck":
            category, text = Category.STUCK, texts.stuck_text(event, self._tz)
        elif event.kind == "exit_rejected":
            # Una salida rechazada por el broker deja la posición abierta: es un error, no ruido.
            category, text = Category.ERROR, texts.exit_rejected_text(event, self._tz)
        elif event.kind == "entry_rejected":
            if event.reason == ReasonCode.REPLAY.value:
                return  # una por vela de reposición: quedan en la DB y en el log, no en el chat
            category, text = Category.REJECTION, texts.rejection_text(event, self._tz)
        else:
            category, text = Category.ERROR, texts.generic_event_text(event, self._tz)
        self._queue_note(category, text, event.ts, event.pair)

    def on_position_opened(self, position: Position, fill: Fill) -> None:
        if self.config.notify.telegram_enabled:
            self._pending_operations.append((position, fill, self.engine.cash))
            return
        self._queue_note(
            Category.ENTRY,
            texts.entry_text(fill, position, self._tz),
            fill.fill_ts,
            position.pair,
            f"{self.instance_name}:{fill.client_order_id}:entry",
        )

    def on_trade_closed(self, trade: Trade, fill: Fill) -> None:
        if self.config.notify.telegram_enabled:
            self._pending_operations.append((trade, fill, self.engine.cash))
            return
        by_stop = trade.exit_reason in (ExitReason.STOP, ExitReason.TRAILING)
        # El efectivo tras la venta es exacto; el total dependería de marks de la vela anterior.
        text = texts.exit_text(trade, fill, self.engine.cash, self._tz)
        self._queue_note(
            Category.STOP if by_stop else Category.EXIT,
            text,
            fill.fill_ts,
            trade.pair,
            f"{self.instance_name}:{fill.client_order_id}:{'stop' if by_stop else 'exit'}",
        )

    def on_feed_event(self, event: FeedEvent) -> None:
        self.store.record_event(
            EventRecord(
                ts=event.ts, kind=event.kind, pair=event.pair, reason=event.detail[:80], payload={}
            )
        )
        self.note(f"{event.kind} {'' if event.pair is None else event.pair.symbol} {event.detail}")
        if event.kind != FEED_RETRY:  # los reintentos ya se ven en el log; no son un aviso
            self.notifier.notify(
                Notification(
                    ts=event.ts,
                    category=Category.FEED,
                    text=texts.feed_text(event),
                    pair=event.pair,
                )
            )

    def on_broker_events(self, events: list[BrokerEvent]) -> None:
        with self._cycle():
            self.engine.apply_events(events)
            self.persist()
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
        self.flush_notifications()
        self.write_status()

    # ------------------------------------------------------------- CommandBackend (ADR-0012)

    def trades(self) -> Sequence[Trade]:
        return self.store.trades()

    def fills(self) -> Sequence[Fill]:
        return self.store.fills()

    def events(self) -> Sequence[EventRecord]:
        return self.store.events()

    def snapshots(self) -> Sequence[PortfolioSnapshot]:
        return self.store.snapshots()

    def now_ms(self) -> int:
        return self.exchange.now_ms()

    @property
    def initial_cash(self) -> Decimal:
        return self.config.backtest.initial_cash

    @property
    def _quote(self) -> str:
        return self.config.strategy.pairs[0].quote

    def retry_pending_fills(self) -> None:
        """Órdenes que esperaban precio: se reintentan en cada tick del watcher (I8)."""
        if self._next_open is None or not self.broker.pending_orders():
            return
        events = self.broker.fill_pending(self._next_open)
        if events:
            self.on_broker_events(events)

    # ------------------------------------------------------------- persistencia y status

    def persist(self) -> None:
        self.store.save_state(ENGINE_STATE_KEY, self.engine.state().to_dict())
        self.store.save_state(
            SESSION_STATE_KEY,
            {"version": __version__, "saved_ts": self.exchange.now_ms(), "mode": self.config.mode},
        )

    def status_payload(self, phase: str = "corriendo") -> dict[str, Any]:
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
            "instance_name": self.instance_name,
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
            "notify": self.notifier.status(),
            "db": {"path": str(self.store.path), "counts": self.store.counts()},
        }

    def write_status(self, phase: str = "corriendo") -> None:
        try:
            self.status.write(self.status_payload(phase), heartbeat_ts=self.exchange.now_ms())
        except OSError as exc:  # el status nunca tumba el bot
            log.warning("paper: no se pudo escribir status.json (%s)", exc)

    # ------------------------------------------------------------- ciclo

    def _stop_requested(self) -> bool:
        return self._stopping

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

    def process(self, bar: Bar) -> None:
        """Un cierre: motor, fills inmediatos, stops, persistencia y status.

        Todo el ciclo va en una transacción: un corte a mitad no deja el cash sin la venta ni la
        posición sin el débito (ADR-0011).
        """
        tf = self.config.strategy.timeframe.ms
        self._next_open = bar.open_time + tf
        with self._cycle():
            self.engine.process_bar(bar)
            self.engine.apply_events(self.broker.fill_pending(self._next_open))
            self.engine.apply_events(self.broker.check_stops())
            self.watcher.ticks += 1
            self.persist()
        self.bars_processed += 1
        self._last_cycle_ts = self.exchange.now_ms()
        self.note(
            f"vela {_iso(bar.open_time)}{' (reposición)' if bar.replay else ''}: "
            f"equity {self.engine.equity():.2f}, posiciones {len(self.engine.positions)}"
        )
        self.flush_notifications()
        self.write_status()

    def stale_for_ms(self) -> int:
        """Milisegundos desde el último ciclo completo (o desde el arranque)."""
        return max(self.exchange.now_ms() - self._last_cycle_ts, 0)

    def is_stale(self) -> bool:
        tf = self.config.strategy.timeframe.ms
        return self.stale_for_ms() > 2 * tf + self.watchdog_grace_ms

    async def _handle_stale(self) -> None:
        text = texts.stale_text(self.stale_for_ms() // 60_000)
        self.note(text)
        # Envío directo: la cola del notificador no llegaría a drenarse antes del `os._exit`.
        with contextlib.suppress(Exception):
            await self.notifier.send_now(text, timeout_s=STALE_ALERT_TIMEOUT_S)
        self.write_status("colgado")
        if self.on_stale is not None:
            self.on_stale()
            return
        with contextlib.suppress(Exception):
            self.store.close()
        os._exit(1)

    async def _watchdog(self, sleep: AsyncSleep) -> None:
        """El healthcheck de compose no reinicia nada: el proceso se vigila a sí mismo (I3)."""
        while not self._stopping:
            await sleep(self.watchdog_interval_s)
            if not self._stopping and self.is_stale():
                await self._handle_stale()
                return

    def _task_done(self, name: str, task: asyncio.Task[None], *, critical: bool = True) -> None:
        """Una tarea auxiliar que muere con excepción para el proceso ordenadamente (I5).

        Las no críticas (notificador, resumen diario) solo se anotan: Telegram caído no frena
        el ciclo de velas (ADR-0012).
        """
        if task.cancelled():
            return
        exc = task.exception()
        if exc is None:
            return
        log.error("paper: la tarea %s murió: %r", name, exc)
        if critical:
            self.note(f"tarea {name} caída: {exc!r}; parada solicitada")  # técnico, al log
            self.notifier.notify(
                Notification(
                    ts=self.exchange.now_ms(),
                    category=Category.ERROR,
                    text=texts.task_dead_text(name, exc, critical=True),
                )
            )
            self.request_stop()
        else:
            self.note(f"tarea {name} caída: {exc!r}; el paper sigue sin ella")

    # ------------------------------------------------------------- resumen diario (ADR-0012)

    def _daily_key(self, now_ms: int) -> int | None:
        """Día local (en `notify.timezone`) cuya hora de resumen ya pasó; None si aún no."""
        zone = ZoneInfo(self.config.notify.timezone)
        local = datetime.fromtimestamp(now_ms / 1000, tz=UTC).astimezone(zone)
        if local.hour < self.config.notify.daily_summary_hour:
            return None
        return local.toordinal()

    async def _daily_loop(self, sleep: AsyncSleep) -> None:
        # Al arrancar se marca el día en curso como enviado: un reinicio no repite el resumen.
        self._last_daily_key = self._daily_key(self.exchange.now_ms())
        while True:
            await sleep(DAILY_CHECK_S)
            if self._stop_requested():  # vía método: mypy no estrecha el atributo entre awaits
                return
            key = self._daily_key(self.exchange.now_ms())
            if key is not None and key != self._last_daily_key:
                self._last_daily_key = key
                self.send_daily_summary()

    def send_daily_summary(self) -> None:
        try:
            text = self.commands.daily()
        except Exception as exc:  # el resumen nunca tumba el bot
            log.warning("paper: no se pudo armar el resumen diario (%s)", exc)
            return
        self.notifier.notify(
            Notification(ts=self.exchange.now_ms(), category=Category.DAILY, text=text)
        )

    async def run(self, *, max_bars: int | None = None, install_signals: bool = True) -> int:
        """Corre hasta `request_stop()` (o `max_bars`). Devuelve la cantidad de velas procesadas."""
        if install_signals:
            self._install_signal_handlers()
        notifier_task = asyncio.create_task(self.notifier.run())
        notifier_task.add_done_callback(lambda t: self._task_done("notifier", t, critical=False))
        self.note(
            f"paper {self.strategy.name} {self.config.strategy.timeframe.value} "
            f"{', '.join(p.symbol for p in self.config.strategy.pairs)}: "
            f"{'reanudado desde la DB' if self.restored else 'arranque limpio'}, "
            f"{self.feed.replay_pending} velas de reposición"
        )
        self.notifier.notify(
            Notification(
                ts=self.exchange.now_ms(),
                category=Category.LIFECYCLE,
                text=texts.startup_text(
                    self.config.mode.value,
                    restored=self.restored,
                    replay=self.feed.replay_pending,
                    positions=len(self.engine.positions),
                    equity=self.engine.equity(),
                    quote=self._quote,
                ),
            )
        )
        self._last_cycle_ts = self.exchange.now_ms()
        self.write_status("arranque")
        watcher_task = asyncio.create_task(self.watcher.run())
        watcher_task.add_done_callback(lambda t: self._task_done("watcher", t))
        watchdog_task = asyncio.create_task(self._watchdog(self._sleep))
        watchdog_task.add_done_callback(lambda t: self._task_done("watchdog", t))
        aux: list[asyncio.Task[None]] = [watcher_task, watchdog_task]
        if self.daily_summary:
            daily_task = asyncio.create_task(self._daily_loop(self._sleep))
            daily_task.add_done_callback(lambda t: self._task_done("daily", t, critical=False))
            aux.append(daily_task)
        try:
            async for bar in self.feed:
                self.process(bar)
                if max_bars is not None and self.bars_processed >= max_bars:
                    self.request_stop()
                    break
        finally:
            self.request_stop()
            for task in aux:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
            if not self._cycle_failed:
                with self._cycle():
                    self.persist()
                self.flush_notifications()
            self.note(f"paper detenido tras {self.bars_processed} velas")
            self.notifier.notify(
                Notification(
                    ts=self.exchange.now_ms(),
                    category=Category.LIFECYCLE,
                    text=texts.shutdown_text(
                        self.bars_processed,
                        self.engine.equity(),
                        len(self.engine.positions),
                        self._quote,
                    ),
                )
            )
            self.write_status("detenido")
            # Primero se apaga el notificador (drena la cola y deja de atender comandos) y recién
            # después se cierra la DB: un `/status` tardío no encuentra el store cerrado (I6).
            self.notifier.stop()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await asyncio.wait_for(notifier_task, NOTIFIER_STOP_TIMEOUT_S)
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


def _build_notifier(
    config: BotConfig, on_command: Callable[[str], str], store: SqliteStore | None = None
) -> Notifier:
    """Telegram si está habilitado (token y chat_id vienen del entorno); si no, el log."""
    name = config.notify.instance_name or config.strategy.name
    prefix = f"[{config.mode.value.upper()} | {name}] "
    if not config.notify.telegram_enabled:
        return LogNotifier(config.notify.events, prefix=prefix)
    from tradingbot.notify.telegram import TelegramNotifier  # import pesado: solo si se usa

    token = config.telegram_bot_token
    chat_id = config.telegram_chat_id
    if token is None or chat_id is None:  # BotConfig ya lo valida; doble chequeo defensivo
        msg = "notify.telegram_enabled requiere TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID"
        raise ConfigError(msg)
    return TelegramNotifier(
        token.get_secret_value(),
        chat_id.get_secret_value(),
        levels=config.notify.events,
        on_command=lambda text: (
            "Comandos de esta instancia (referencia); no controlan las candidatas.\n"
            + on_command(text)
        ),
        receive_commands=config.notify.telegram_receive_commands,
        prefix=prefix,
        outbox=store,
    )


def build_paper_session(
    config: BotConfig,
    exchange: PaperExchange,
    *,
    store: SqliteStore | None = None,
    status_path: Path | None = None,
    sleep: AsyncSleep = asyncio.sleep,
    notifier: Notifier | None = None,
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
    if notifier is None:
        notifier = _build_notifier(config, lambda text: holder[0].commands.handle(text), store)
    session = PaperSession(
        config=config,
        strategy=strategy,
        exchange=exchange,
        store=store,
        feed=feed,
        broker=broker,
        engine=engine,
        watcher=StopWatcher(
            broker,
            config.execution.stop_watch_interval_s,
            on_broker_events,
            sleep=sleep,
            pre_tick=lambda: holder[0].retry_pending_fills(),
        ),
        kill_switch=kill_switch,
        status=status,
        restored=restore is not None,
        _sleep=sleep,
        notifier=notifier,
    )
    holder.append(session)
    for event in early_events:
        session.on_feed_event(event)
    if dropped:
        session.note(f"{dropped} orden(es) pendientes de la sesión anterior canceladas")
    return session
