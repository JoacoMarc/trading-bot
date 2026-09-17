"""Avisos y comandos en la sesión de paper (ADR-0012): buffer tras el commit, tareas no críticas."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from tests.factories import BTC
from tests.paper.test_runner import FakePaperExchange, paper_config, rising_days
from tradingbot.notify import Category, Notification
from tradingbot.paper import build_paper_session
from tradingbot.paper.runner import PaperSession
from tradingbot.persistence import SqliteStore


class RecordingNotifier:
    def __init__(self, *, fail_run: bool = False) -> None:
        self.notes: list[Notification] = []
        self.urgent: list[str] = []
        self.fail_run = fail_run
        self.stopped = False
        self._wake: asyncio.Event | None = None

    def notify(self, note: Notification) -> None:
        self.notes.append(note)

    async def run(self) -> None:
        if self.fail_run:
            msg = "telegram roto"
            raise RuntimeError(msg)
        self._wake = asyncio.Event()
        if self.stopped:
            return
        await self._wake.wait()

    def stop(self) -> None:
        self.stopped = True
        if self._wake is not None:
            self._wake.set()

    async def send_now(self, text: str, *, timeout_s: float = 5.0) -> bool:
        self.urgent.append(text)
        return True

    def status(self) -> dict[str, Any]:
        return {"backend": "recording", "sent": len(self.notes), "errors": 0, "dropped": 0}

    def texts(self, category: Category) -> list[str]:
        return [n.text for n in self.notes if n.category is category]


def build(tmp_path: Path, notifier: RecordingNotifier) -> tuple[PaperSession, FakePaperExchange]:
    candles = rising_days(8)
    exchange = FakePaperExchange({BTC: candles}, now_ms=candles[30].open_time + 300_000)
    exchange.last[BTC] = "105"
    config = paper_config(tmp_path)
    session = build_paper_session(config, exchange, sleep=exchange.sleep, notifier=notifier)
    return session, exchange


async def test_session_announces_lifecycle_and_entry_after_commit(tmp_path: Path) -> None:
    notifier = RecordingNotifier()
    session, _exchange = build(tmp_path, notifier)
    assert session.engine.listener is session
    await session.run(max_bars=2, install_signals=False)

    lifecycle = notifier.texts(Category.LIFECYCLE)
    assert lifecycle[0].startswith("paper regime_bh 4h BTC/USDT: arranque limpio")
    assert lifecycle[-1].startswith("paper detenido tras 2 velas")
    entries = notifier.texts(Category.ENTRY)
    assert len(entries) == 1
    assert entries[0].startswith("compra BTC/USDT:")
    assert "stop" in entries[0]
    assert "-20.0 %" in entries[0]
    assert session._pending_notes == []  # todo lo del ciclo salió tras el commit
    assert notifier.stopped
    status = session.status_payload("detenido")
    assert status["notify"]["backend"] == "recording"


async def test_commands_read_the_session_and_write_the_kill_switch(tmp_path: Path) -> None:
    notifier = RecordingNotifier()
    session, _exchange = build(tmp_path, notifier)
    await session.run(max_bars=2, install_signals=False)
    session.store = type(session.store)(session.config.db_path)  # reabrir: `run` la cerró

    status = session.commands.handle("/status")
    assert status.startswith("paper regime_bh 4h BTC/USDT - corriendo")
    assert "BTC/USDT: " in status
    assert "equity" in status
    health = session.commands.handle("/health")
    assert "velas 2, fills 1" in health
    assert "avisos (recording)" in health
    assert session.commands.handle("/trades") == "sin trades cerrados"
    daily = session.commands.handle("/daily")
    assert daily.startswith("resumen 24 h")

    switch = session.kill_switch
    assert not switch.path.exists()
    session.commands.handle("/pause")
    assert switch.poll().active
    session.commands.handle("/stop flatten")
    session.commands.handle("si")
    assert switch.poll().flatten
    session.commands.handle("/resume breaker")
    assert not switch.path.exists()
    assert switch.consume_resume()
    session.store.close()


async def test_a_dead_notifier_does_not_stop_the_paper(tmp_path: Path) -> None:
    notifier = RecordingNotifier(fail_run=True)
    session, _exchange = build(tmp_path, notifier)
    processed = await session.run(max_bars=2, install_signals=False)
    assert processed == 2
    lines = list(session.recent)
    assert any("tarea notifier caída" in line and "sigue sin ella" in line for line in lines)
    bars = [i for i, line in enumerate(lines) if " UTC vela " in line]
    stop = next(i for i, line in enumerate(lines) if "parada solicitada" in line)
    assert len(bars) == 2
    assert stop > bars[-1]  # la parada llegó recién por max_bars, tras las dos velas


class FailingStore(SqliteStore):
    """Falla una vez al guardar el `state`: la transacción del ciclo hace rollback."""

    fail_once = False  # el constructor ya escribe `schema_version`: la falla se arma después

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_once = True

    def save_state(self, key: str, value: Mapping[str, Any]) -> None:
        if self.fail_once:
            self.fail_once = False
            msg = "disco lleno"
            raise RuntimeError(msg)
        super().save_state(key, value)


async def test_a_rolled_back_cycle_notifies_nothing(tmp_path: Path) -> None:
    candles = rising_days(8)
    exchange = FakePaperExchange({BTC: candles}, now_ms=candles[30].open_time + 300_000)
    exchange.last[BTC] = "105"
    config = paper_config(tmp_path)
    notifier = RecordingNotifier()
    store = FailingStore(config.db_path)
    session = build_paper_session(
        config, exchange, store=store, sleep=exchange.sleep, notifier=notifier
    )
    with pytest.raises(RuntimeError, match="disco lleno"):
        await session.run(max_bars=1, install_signals=False)
    # La compra se decidió y llenó en memoria, pero la transacción falló: ni fill en la DB ni aviso.
    assert notifier.texts(Category.ENTRY) == []
    assert session._pending_notes == []
    reopened = SqliteStore(config.db_path)
    assert reopened.fills() == ()
    reopened.close()


async def test_watchdog_alert_is_sent_directly_before_exiting(tmp_path: Path) -> None:
    notifier = RecordingNotifier()
    session, exchange = build(tmp_path, notifier)
    session.on_stale = lambda: None
    exchange.now += 2 * 4 * 3_600_000 + 300_001
    await session._handle_stale()
    assert len(notifier.urgent) == 1
    assert notifier.urgent[0].startswith("watchdog: sin ciclo completo")
    assert notifier.texts(Category.ERROR) == []  # no pasó por la cola: no llegaría a drenarse
    session.store.close()


def test_daily_key_follows_the_local_summary_hour(tmp_path: Path) -> None:
    notifier = RecordingNotifier()
    session, exchange = build(tmp_path, notifier)
    # daily_summary_hour = 9 en America/Argentina/Buenos_Aires (UTC-3): 12:00 UTC.
    noon_utc = (exchange.now_ms() // 86_400_000) * 86_400_000 + 12 * 3_600_000
    assert session._daily_key(noon_utc - 3_600_000) is None  # 08:00 local: todavía no
    key = session._daily_key(noon_utc)
    assert key is not None
    assert session._daily_key(noon_utc + 86_400_000) == key + 1
    session.send_daily_summary()
    assert notifier.texts(Category.DAILY)[0].startswith("resumen 24 h")
    session.store.close()
