"""`EngineListener` (ADR-0012): el motor avisa lo mismo que persiste, y sin listener no cambia."""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

import pytest

from tests.engine.fakes import H4, ScriptedStrategy, bars_from, build_engine, candles_from_prices
from tests.factories import BTC, T0
from tradingbot.domain import ExitReason, Fill, Position, Trade
from tradingbot.engine import Engine
from tradingbot.persistence import TradeStore
from tradingbot.persistence.store import EventRecord
from tradingbot.risk.protections import KillSwitchState

ROUND_TRIP = [
    ("100", "101", "99", "100"),
    ("102", "104", "101", "103"),
    ("103", "105", "102", "104"),
    ("110", "111", "109", "110"),
    ("110", "111", "109", "110"),
]


class Recorder:
    def __init__(self) -> None:
        self.events: list[EventRecord] = []
        self.opened: list[tuple[Position, Fill]] = []
        self.closed: list[tuple[Trade, Fill]] = []

    def on_event(self, event: EventRecord) -> None:
        self.events.append(event)

    def on_position_opened(self, position: Position, fill: Fill) -> None:
        self.opened.append((position, fill))

    def on_trade_closed(self, trade: Trade, fill: Fill) -> None:
        self.closed.append((trade, fill))


class ActiveSwitch:
    def poll(self) -> KillSwitchState:
        return KillSwitchState(active=True)

    def consume_resume(self) -> bool:
        return False


def test_listener_sees_open_close_and_every_recorded_event() -> None:
    candles = candles_from_prices(ROUND_TRIP)
    strategy = ScriptedStrategy({T0: ("enter", "90"), T0 + 2 * H4: ("exit", None)})
    engine, store, _broker = build_engine(strategy, bars_from(candles), {BTC: candles})
    recorder = Recorder()
    engine.listener = recorder
    asyncio.run(engine.run())

    assert len(recorder.opened) == 1
    position, fill = recorder.opened[0]
    assert position.pair == BTC
    assert position.qty == Decimal("9.99")
    assert fill.price == Decimal("102.06")
    assert position.stop_price < position.entry_price
    assert len(recorder.closed) == 1
    trade, sell = recorder.closed[0]
    assert trade.exit_reason is ExitReason.SIGNAL
    assert sell.price == trade.exit_price
    assert store.trades() == (trade,)
    assert recorder.events == list(store.events())  # nada se avisa sin persistirse


def test_listener_receives_protection_events_in_store_order() -> None:
    candles = candles_from_prices(ROUND_TRIP)
    strategy = ScriptedStrategy({T0: ("enter", "90")})
    engine, store, _broker = build_engine(
        strategy, bars_from(candles), {BTC: candles}, kill_switch=ActiveSwitch()
    )
    recorder = Recorder()
    engine.listener = recorder
    asyncio.run(engine.run())

    kinds = [e.kind for e in recorder.events]
    assert kinds[0] == "protection_triggered"  # kill switch activo desde la primera vela
    assert "entry_rejected" in kinds  # la entrada se rechazó por el kill switch
    assert recorder.events == list(store.events())
    assert recorder.opened == []


def test_engine_with_and_without_listener_persist_exactly_the_same() -> None:
    candles = candles_from_prices(ROUND_TRIP)

    def run_once(with_listener: bool) -> tuple[Engine, TradeStore]:
        strategy = ScriptedStrategy({T0: ("enter", "90"), T0 + 2 * H4: ("exit", None)})
        engine, store, _broker = build_engine(
            strategy, bars_from(candles), {BTC: candles}, kill_switch=None
        )
        if with_listener:
            engine.listener = Recorder()
        asyncio.run(engine.run())
        return engine, store

    plain_engine, plain = run_once(with_listener=False)
    heard_engine, heard = run_once(with_listener=True)
    assert plain_engine.listener is None
    assert plain.events() == heard.events()
    assert plain.trades() == heard.trades()
    assert plain.fills() == heard.fills()
    assert plain.orders() == heard.orders()
    assert plain.snapshots() == heard.snapshots()
    assert plain_engine.cash == heard_engine.cash
    assert plain_engine.stats == heard_engine.stats


class Exploding(Recorder):
    def on_trade_closed(self, trade: Trade, fill: Fill) -> None:
        msg = "listener roto"
        raise RuntimeError(msg)


def test_a_failing_listener_is_logged_and_the_cycle_persists(
    caplog: pytest.LogCaptureFixture,
) -> None:
    candles = candles_from_prices(ROUND_TRIP)
    strategy = ScriptedStrategy({T0: ("enter", "90"), T0 + 2 * H4: ("exit", None)})
    engine, store, broker = build_engine(strategy, bars_from(candles), {BTC: candles})
    engine.listener = Exploding()
    with caplog.at_level(logging.ERROR, logger="tradingbot.engine.engine"):
        asyncio.run(engine.run())
    assert "el listener falló en on_trade_closed" in caplog.text
    assert len(store.trades()) == 1  # la venta se persistió igual
    assert engine.positions.get(BTC) is None
    assert broker.get_stop(BTC) is None
    assert engine.cash > Decimal("10000")  # el trade fue ganador y el cash lo refleja
