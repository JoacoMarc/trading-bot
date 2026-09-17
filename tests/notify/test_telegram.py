"""`TelegramNotifier` (ADR-0012) con envío falso: cola, niveles, errores, whitelist y reintentos."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from telegram import Chat, Message, Update
from telegram.error import NetworkError, RetryAfter
from telegram.ext import filters

from tradingbot.notify import Category, Level, Notification
from tradingbot.notify.telegram import (
    COMMAND_ERROR_REPLY,
    NOISY_LOGGERS,
    TelegramNotifier,
    run_smoke_test,
)

CHAT = "42"


class FakeSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, bool]] = []
        self.failures: list[Exception] = []

    async def __call__(self, text: str, silent: bool) -> None:
        if self.failures:
            raise self.failures.pop(0)
        self.sent.append((text, silent))


class FakeSleep:
    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def note(category: Category, text: str) -> Notification:
    return Notification(ts=0, category=category, text=text)


def make_notifier(sender: FakeSender, **kwargs: object) -> TelegramNotifier:
    return TelegramNotifier(
        "123:token",
        CHAT,
        sender=sender,
        levels={Category.FEED: Level.SILENT, Category.REJECTION: Level.OFF},
        **kwargs,  # type: ignore[arg-type]
    )


async def run_until_drained(notifier: TelegramNotifier) -> None:
    task = asyncio.create_task(notifier.run())
    await asyncio.sleep(0)
    notifier.stop()
    await asyncio.wait_for(task, 2.0)


async def test_levels_decide_sound_and_off_is_not_sent() -> None:
    sender = FakeSender()
    notifier = make_notifier(sender)
    notifier.notify(note(Category.ENTRY, "compra"))
    notifier.notify(note(Category.FEED, "feed_late"))
    notifier.notify(note(Category.REJECTION, "rechazo"))
    assert notifier.status()["queued"] == 2
    await run_until_drained(notifier)
    assert sender.sent == [("compra", False), ("feed_late", True)]
    status = notifier.status()
    assert status["sent"] == 2
    assert status["errors"] == 0
    assert status["connected"] is False  # se desconectó al terminar


async def test_full_queue_drops_the_oldest() -> None:
    sender = FakeSender()
    notifier = make_notifier(sender, queue_size=2)
    for i in range(4):
        notifier.notify(note(Category.ENTRY, f"m{i}"))
    assert notifier.status()["dropped"] == 2
    assert notifier.status()["queued"] == 2
    await run_until_drained(notifier)
    assert [t for t, _ in sender.sent] == ["m2", "m3"]


def test_stop_sentinel_enters_a_full_queue_and_stays_last() -> None:
    notifier = make_notifier(FakeSender(), queue_size=2)
    for i in range(2):
        notifier.notify(note(Category.ENTRY, f"m{i}"))
    notifier.stop()  # llena: desplaza al más viejo, el centinela queda al final
    assert notifier.status()["dropped"] == 1
    notifier.notify(note(Category.ENTRY, "tarde"))  # llega después del stop: se ignora
    queue = notifier._queue
    items = [queue.get_nowait() for _ in range(queue.qsize())]
    assert items == [("m1", False), None]
    assert notifier.status()["dropped"] == 1


async def test_send_errors_are_counted_and_do_not_stop_the_drain() -> None:
    sender = FakeSender()
    sender.failures = [NetworkError("boom")]
    notifier = make_notifier(sender)
    notifier.notify(note(Category.ENTRY, "a"))
    notifier.notify(note(Category.ENTRY, "b"))
    await run_until_drained(notifier)
    assert [t for t, _ in sender.sent] == ["b"]
    assert notifier.status()["errors"] == 1
    assert notifier.status()["sent"] == 1


async def test_retry_after_waits_and_retries_once() -> None:
    sender = FakeSender()
    sender.failures = [RetryAfter(timedelta(seconds=3))]
    sleep = FakeSleep()
    notifier = make_notifier(sender, sleep=sleep)
    notifier.notify(note(Category.ENTRY, "a"))
    await run_until_drained(notifier)
    assert sleep.calls == [4.0]  # retry_after + 1 s
    assert [t for t, _ in sender.sent] == ["a"]
    assert notifier.status()["errors"] == 0


async def test_persistent_rate_limit_drops_the_message() -> None:
    sender = FakeSender()
    sender.failures = [RetryAfter(1), RetryAfter(1)]
    notifier = make_notifier(sender, sleep=FakeSleep())
    notifier.notify(note(Category.ENTRY, "a"))
    await run_until_drained(notifier)
    assert sender.sent == []
    assert notifier.status()["errors"] == 1


def test_dispatch_whitelists_the_chat_and_guards_the_command_handler() -> None:
    seen: list[str] = []

    def on_command(text: str) -> str:
        seen.append(text)
        if text == "/boom":
            msg = "roto"
            raise RuntimeError(msg)
        return f"ok {text}"

    notifier = TelegramNotifier("123:token", CHAT, sender=FakeSender(), on_command=on_command)
    assert notifier.dispatch("7", "/status") is None
    assert notifier.dispatch("7", "/status") is None
    assert notifier.ignored_chats == {"7"}
    assert seen == []
    assert notifier.dispatch(CHAT, "/status") == "ok /status"
    reply = notifier.dispatch(CHAT, "/boom")
    assert reply == COMMAND_ERROR_REPLY  # nada del traceback llega al chat
    assert notifier.status()["errors"] == 1
    assert notifier.status()["commands"] == 2


def test_dispatch_without_handler_echoes() -> None:
    notifier = TelegramNotifier("123:token", CHAT, sender=FakeSender())
    reply = notifier.dispatch(CHAT, "hola")
    assert reply is not None
    assert reply.endswith("recibio: hola")


async def test_connect_failures_back_off_and_do_not_raise() -> None:
    sender = FakeSender()
    sleep = FakeSleep()
    notifier = make_notifier(sender, sleep=sleep, startup_backoff_s=5.0, startup_backoff_max_s=8.0)
    attempts = {"n": 0}
    original = notifier._connect

    async def flaky_connect() -> None:
        attempts["n"] += 1
        if attempts["n"] <= 2:
            raise NetworkError("sin red")
        await original()

    notifier._connect = flaky_connect  # type: ignore[method-assign]
    notifier.notify(note(Category.LIFECYCLE, "arranque"))
    await run_until_drained(notifier)
    assert attempts["n"] == 3
    assert sleep.calls == [5.0, 8.0]  # backoff exponencial acotado
    assert notifier.status()["errors"] == 2
    assert [t for t, _ in sender.sent] == ["arranque"]


async def test_stop_during_connect_retries_ends_the_run() -> None:
    notifier = make_notifier(FakeSender(), startup_backoff_s=5.0)

    async def always_fails() -> None:
        raise NetworkError("sin red")

    async def stop_on_sleep(_seconds: float) -> None:
        notifier.stop()

    notifier._connect = always_fails  # type: ignore[method-assign]
    notifier._sleep = stop_on_sleep
    await asyncio.wait_for(notifier.run(), 2.0)
    assert notifier.status()["connected"] is False


def test_real_application_is_built_without_network() -> None:
    notifier = TelegramNotifier("123456:ABC-DEF", CHAT)
    app = notifier._build_app()
    assert app.bot.token == "123456:ABC-DEF"
    assert sum(len(group) for group in app.handlers.values()) == 1


def test_constructing_the_notifier_silences_the_loggers_that_print_the_token() -> None:
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.NOTSET)
    logging.getLogger().setLevel(logging.INFO)
    TelegramNotifier("123456:ABC-DEF", CHAT)
    for name in NOISY_LOGGERS:
        assert logging.getLogger(name).getEffectiveLevel() >= logging.WARNING


def test_handler_filter_ignores_edited_messages_and_non_text() -> None:
    chat = Chat(id=int(CHAT), type="private")
    text = Message(message_id=1, date=datetime.now(UTC), chat=chat, text="/pause")
    sticker_like = Message(message_id=2, date=datetime.now(UTC), chat=chat)
    accepted = filters.UpdateType.MESSAGE & filters.TEXT
    assert accepted.check_update(Update(update_id=1, message=text))
    assert not accepted.check_update(Update(update_id=2, edited_message=text))
    assert not accepted.check_update(Update(update_id=3, message=sticker_like))


async def test_on_update_replies_only_to_the_whitelisted_chat() -> None:
    replies: list[str] = []

    async def reply_text(text: str) -> None:
        replies.append(text)

    notifier = TelegramNotifier(
        "123:token", CHAT, sender=FakeSender(), on_command=lambda t: f"ok {t}"
    )
    good = SimpleNamespace(
        message=SimpleNamespace(text="/status", reply_text=reply_text),
        effective_chat=SimpleNamespace(id=int(CHAT)),
    )
    stranger = SimpleNamespace(
        message=SimpleNamespace(text="/stop flatten", reply_text=reply_text),
        effective_chat=SimpleNamespace(id=7),
    )
    await notifier._on_update(good, None)  # type: ignore[arg-type]
    await notifier._on_update(stranger, None)  # type: ignore[arg-type]
    assert replies == ["ok /status"]


class FakeUpdater:
    def __init__(self) -> None:
        self.running = False
        self.starts = 0

    async def start_polling(self, **_kwargs: object) -> None:
        self.running = True
        self.starts += 1

    async def stop(self) -> None:
        self.running = False


class FakeApp:
    def __init__(self) -> None:
        self.updater = FakeUpdater()
        self.running = False
        self.initialized = 0
        self.shutdowns = 0

    async def initialize(self) -> None:
        self.initialized += 1

    async def start(self) -> None:
        self.running = True

    async def stop(self) -> None:
        self.running = False

    async def shutdown(self) -> None:
        self.shutdowns += 1


async def test_dead_polling_triggers_a_reconnect() -> None:
    apps: list[FakeApp] = []

    def factory() -> FakeApp:
        app = FakeApp()
        apps.append(app)
        return app

    sender = FakeSender()
    notifier = make_notifier(sender, app_factory=factory, poll_check_s=0.01)
    task = asyncio.create_task(notifier.run())
    await asyncio.sleep(0.05)
    assert notifier.status()["polling"] is True
    apps[0].updater.running = False  # el Updater murió con el proceso vivo
    await asyncio.sleep(0.1)
    assert notifier.status()["reconnects"] == 1
    assert len(apps) == 2
    assert apps[0].shutdowns == 1
    assert notifier.status()["polling"] is True
    notifier.notify(note(Category.ENTRY, "sigo vivo"))
    notifier.stop()
    await asyncio.wait_for(task, 2.0)
    assert [t for t, _ in sender.sent] == ["sigo vivo"]
    assert apps[1].shutdowns == 1


async def test_send_now_bypasses_the_queue_and_never_raises() -> None:
    sender = FakeSender()
    notifier = make_notifier(sender)
    assert await notifier.send_now("antes de conectar") is False  # sin conexión: no manda
    task = asyncio.create_task(notifier.run())
    await asyncio.sleep(0)
    assert await notifier.send_now("urgente") is True
    sender.failures = [NetworkError("boom")]
    assert await notifier.send_now("falla") is False
    notifier.stop()
    await asyncio.wait_for(task, 2.0)
    assert [t for t, _ in sender.sent] == ["urgente"]
    assert notifier.status()["errors"] == 1


async def test_smoke_test_sends_the_probe_with_an_injected_sender() -> None:
    sender = FakeSender()
    status, received = await run_smoke_test(
        "123:token", CHAT, seconds=0.02, sender=sender, poll_s=0.01
    )
    assert status["sent"] == 1
    assert "prueba de tradingbot" in sender.sent[0][0]
    assert received == []
