"""Aislamiento, un único receptor y avisos persistentes tras commit."""

from __future__ import annotations

import asyncio
from functools import partial
from pathlib import Path

import pytest
import yaml
from telegram.error import NetworkError

from tests.factories import BTC
from tests.notify.test_telegram import FakeApp, FakeSender
from tests.paper.test_notifications import RecordingNotifier
from tests.paper.test_runner import FakePaperExchange, paper_config, rising_days
from tradingbot.config.settings import BotConfig
from tradingbot.notify.telegram import TelegramNotifier
from tradingbot.paper import build_paper_session
from tradingbot.persistence.sqlite import SqliteStore
from tradingbot.risk.protections import FileKillSwitch


async def test_three_notifiers_share_one_receiver() -> None:
    apps = [FakeApp() for _ in range(3)]
    senders = [FakeSender() for _ in range(3)]
    bots = [
        TelegramNotifier(
            "test:token",
            "42",
            sender=senders[i],
            receive_commands=i == 0,
            app_factory=partial(lambda app: app, apps[i]),
            prefix=f"[PAPER | {i}] ",
        )
        for i in range(3)
    ]
    tasks = [asyncio.create_task(bot.run()) for bot in bots]
    await asyncio.sleep(0.01)
    assert [app.updater.starts for app in apps] == [1, 0, 0]
    for bot in bots:
        await bot._check_polling()
        assert await bot.send_now("prueba")
    assert [app.updater.starts for app in apps] == [1, 0, 0]
    assert bots[1].dispatch("42", "/pause") is None
    assert bots[1].status()["polling"] is False
    assert senders[2].sent == [("[PAPER | 2] prueba", False)]
    for bot in bots:
        bot.stop()
    await asyncio.gather(*tasks)


def test_real_send_only_app_has_no_updater_or_handlers() -> None:
    bot = TelegramNotifier("123:ABC", "42", receive_commands=False)
    app = bot._build_app()
    assert app.updater is None
    assert app.handlers == {}


def test_outbox_is_atomic_idempotent_and_compatible(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "paper.db")

    def failed_cycle() -> None:
        with store.transaction():
            store.enqueue_notification("entry:1", "compra", False, 1)
            raise RuntimeError("rollback")

    with pytest.raises(RuntimeError, match="rollback"):
        failed_cycle()
    assert store.pending_notification_count() == 0
    store.enqueue_notification("entry:1", "compra", False, 1)
    store.enqueue_notification("entry:1", "duplicada", False, 2)
    assert len(store.pending_notifications(10)) == 1
    assert store.load_state("schema_version") == {"version": 1}
    store.close()
    restored = SqliteStore(tmp_path / "paper.db")
    assert restored.pending_notifications(10)[0]["text"] == "compra"
    restored.finish_notification("entry:1", 3)
    restored.enqueue_notification("entry:1", "otra vez", False, 4)
    assert restored.pending_notification_count() == 0
    restored.close()


async def test_outbox_recovers_network_failure_after_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = [100.0]
    monkeypatch.setattr("tradingbot.notify.telegram.time.time", lambda: now[0])
    store = SqliteStore(tmp_path / "paper.db")
    store.enqueue_notification("x", "[PAPER | prueba] compra", False, 1)
    sender = FakeSender()
    sender.failures = [NetworkError("sin conexión")]
    first = TelegramNotifier("123:token", "42", sender=sender, outbox=store)
    await first._connect()
    await first.deliver_outbox()
    assert store.pending_notification_count() == 1
    assert store.pending_notifications(100_000) == []  # respeta backoff
    await first._disconnect()
    store.close()
    restored = SqliteStore(tmp_path / "paper.db")
    second = TelegramNotifier("123:token", "42", sender=sender, outbox=restored)
    now[0] += 3
    await second._connect()
    await second.deliver_outbox()
    await second.deliver_outbox()
    assert sender.sent == [("[PAPER | prueba] compra", False)]
    assert restored.pending_notification_count() == 0
    await second._disconnect()
    restored.close()


class BrokenOutbox(SqliteStore):
    def enqueue_notification(self, delivery_id: str, text: str, silent: bool, ts: int) -> None:
        raise RuntimeError("outbox sin espacio")


@pytest.mark.parametrize("failure", ["none", "insert", "format"])
async def test_fill_and_notification_commit_together(
    tmp_path: Path,
    failure: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken = failure != "none"
    if failure == "format":

        def fail_format(*args: object) -> str:
            raise RuntimeError("outbox sin espacio")

        monkeypatch.setattr("tradingbot.paper.runner.texts.entry_text", fail_format)
    base = paper_config(tmp_path)
    config = BotConfig(
        **{
            **base.public_dump(),
            "notify": {"telegram_enabled": True, "instance_name": "Referencia"},
            "telegram_bot_token": "123:test",
            "telegram_chat_id": "42",
        }
    )
    store = (BrokenOutbox if failure == "insert" else SqliteStore)(config.db_path)
    candles = rising_days(8)
    exchange = FakePaperExchange({BTC: candles}, now_ms=candles[30].open_time + 300_000)
    exchange.last[BTC] = "105"
    notifier = RecordingNotifier()
    session = build_paper_session(
        config, exchange, store=store, sleep=exchange.sleep, notifier=notifier
    )
    if broken:
        with pytest.raises(RuntimeError, match="outbox sin espacio"):
            await session.run(max_bars=2, install_signals=False)
    else:
        await session.run(max_bars=2, install_signals=False)
    reopened = SqliteStore(config.db_path)
    assert len(reopened.fills()) == (0 if broken else 1)
    assert reopened.pending_notification_count() == (0 if broken else 1)
    if broken:
        assert reopened.load_state("engine") is None
    else:
        assert reopened.pending_notifications(10**15)[0]["text"].startswith("[PAPER | Referencia]")
    reopened.close()


def test_compose_and_controls_are_isolated(tmp_path: Path) -> None:
    config = yaml.safe_load(Path("compose.candidates.yaml").read_text())
    assert config["name"] != yaml.safe_load(Path("compose.yaml").read_text())["name"]
    services = list(config["services"].values())
    for service in services:
        assert (
            "env_file" not in service
        )  # no heredar overrides de riesgo/estrategia de la referencia
        assert service["environment"]["TRADINGBOT_NOTIFY__TELEGRAM_RECEIVE_COMMANDS"] == "false"
    logs = [next(v for v in s["volumes"] if v.endswith(":/app/logs")) for s in services]
    dbs = [next(v for v in s["volumes"] if v.endswith(":/app/db")) for s in services]
    assert len(set(logs)) == len(set(dbs)) == 2
    switches = [FileKillSwitch(tmp_path / str(i) / "STOP") for i in range(3)]
    switches[1].activate(flatten=True)
    assert [s.poll().active for s in switches] == [False, True, False]
    stores = [SqliteStore(tmp_path / str(i) / "paper.db") for i in range(3)]
    stores[1].save_state("cash", {"value": "123"})
    assert stores[0].load_state("cash") is None
    assert stores[2].load_state("cash") is None
    for store in stores:
        store.close()


@pytest.mark.parametrize("by_stop", [False, True])
async def test_exit_notice_survives_restart(tmp_path: Path, by_stop: bool) -> None:
    base = paper_config(tmp_path)
    config = BotConfig(
        **{
            **base.public_dump(),
            "notify": {"telegram_enabled": True, "instance_name": "Referencia"},
            "telegram_bot_token": "123:test",
            "telegram_chat_id": "42",
        }
    )
    candles = rising_days(10)
    exchange = FakePaperExchange({BTC: candles}, now_ms=candles[30].open_time + 300_000)
    exchange.last[BTC] = "105"
    first = build_paper_session(
        config, exchange, sleep=exchange.sleep, notifier=RecordingNotifier()
    )
    await first.run(max_bars=2, install_signals=False)
    exchange.now = candles[32].open_time + 300_000
    exchange.last[BTC] = "70" if by_stop else "105"
    second = build_paper_session(
        config, exchange, sleep=exchange.sleep, notifier=RecordingNotifier()
    )
    second.kill_switch.activate(flatten=not by_stop)
    await second.run(max_bars=1, install_signals=False)
    restored = SqliteStore(config.db_path)
    assert len(restored.trades()) == 1
    rows = restored.pending_notifications(10**15)
    assert len(rows) == 2
    assert any(row["delivery_id"].endswith(":stop" if by_stop else ":exit") for row in rows)
    sender = FakeSender()
    notifier = TelegramNotifier(
        "123:token", "42", sender=sender, outbox=restored, receive_commands=False
    )
    await notifier._connect()
    await notifier.deliver_outbox()
    assert len(sender.sent) == 2
    assert "Vendió" in sender.sent[1][0]
    assert restored.pending_notification_count() == 0
    await notifier._disconnect()
    restored.close()
