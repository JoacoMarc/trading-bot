"""`TelegramNotifier` (ADR-0012): avisos y comandos por Telegram en el mismo loop de la sesión.

- Envío por cola acotada: `notify()` encola sin esperar; llena, descarta el más viejo. Una tarea
  drena la cola con timeout por mensaje; los errores de Telegram se cuentan y loguean, nunca se
  propagan al ciclo de velas.
- Conexión con reintentos y backoff: un token inválido o Telegram caído no tumban el paper. El
  polling de PTB reintenta solo; sus errores se cuentan (`polling_errors`) y, si el `Updater`
  dejó de correr, el notificador se reconecta.
- Whitelist: solo se atiende el `chat_id` configurado; el resto se ignora (un log por chat).
- Secretos: el token viaja en la URL de cada request y `httpx` la loguea a INFO, así que ese
  logger (y `httpcore`) quedan en WARNING; el `chat_id` tampoco se loguea (regla dura 5).
- Texto plano (sin `parse_mode`): un símbolo raro nunca rompe un envío.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import socket
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from telegram import Update
from telegram.error import RetryAfter, TelegramError
from telegram.ext import AIORateLimiter, Application, ContextTypes, MessageHandler, filters

from tradingbot import __version__
from tradingbot.notify.base import (
    DEFAULT_LEVELS,
    Category,
    Level,
    Notification,
    resolve_level,
    truncate,
)

log = logging.getLogger(__name__)

AsyncSleep = Callable[[float], Awaitable[None]]
Sender = Callable[[str, bool], Awaitable[None]]
CommandFn = Callable[[str], str]
QueueItem = tuple[str, bool] | None  # (texto, silencioso) o el centinela de parada
NOISY_LOGGERS = ("httpx", "httpcore")
COMMAND_ERROR_REPLY = "no pude atender el comando; el detalle quedo en el log del bot"


def silence_token_loggers() -> None:
    """`httpx` imprime la URL completa (con el token) a INFO en cada request."""
    for name in NOISY_LOGGERS:
        logger = logging.getLogger(name)
        if logger.getEffectiveLevel() < logging.WARNING:
            logger.setLevel(logging.WARNING)


class TelegramNotifier:
    def __init__(
        self,
        token: str,
        chat_id: str,
        *,
        levels: Mapping[Category, Level] | None = None,
        on_command: CommandFn | None = None,
        queue_size: int = 200,
        send_timeout_s: float = 10.0,
        startup_backoff_s: float = 30.0,
        startup_backoff_max_s: float = 300.0,
        poll_check_s: float = 30.0,
        sleep: AsyncSleep = asyncio.sleep,
        sender: Sender | None = None,
        app_factory: Callable[[], Any] | None = None,
    ) -> None:
        silence_token_loggers()
        self._app_factory = app_factory  # tests: una Application falsa con el mismo ciclo de vida
        self._token = token
        self._chat_id = str(chat_id).strip()
        self._levels = dict(DEFAULT_LEVELS if levels is None else levels)
        self._on_command = on_command
        self._queue: asyncio.Queue[QueueItem] = asyncio.Queue(maxsize=queue_size)
        self._send_timeout_s = send_timeout_s
        self._backoff_s = startup_backoff_s
        self._backoff_max_s = startup_backoff_max_s
        self._poll_check_s = poll_check_s
        self._sleep = sleep
        self.sender = sender  # inyectable (tests, smoke test); default: el bot de la Application
        self._app: Any = None
        self._connected = False
        self._stopping = False
        self.sent = 0
        self.errors = 0
        self.dropped = 0
        self.commands = 0
        self.polling_errors = 0
        self.reconnects = 0
        self.ignored_chats: set[str] = set()

    # ------------------------------------------------------------- Notifier

    def notify(self, note: Notification) -> None:
        if self._stopping:
            return  # llegó después de `stop()`: la cola ya cerró con el centinela
        level = resolve_level(self._levels, note.category)
        if level is Level.OFF:
            return
        self._enqueue((truncate(note.text), level is Level.SILENT))

    async def send_now(self, text: str, *, timeout_s: float = 5.0) -> bool:
        """Envío directo, sin cola, acotado: para avisar antes de que el proceso muera (I3)."""
        if not self._connected:
            return False
        try:
            await asyncio.wait_for(self._send(truncate(text), False), timeout_s)
        except (TelegramError, OSError, TimeoutError) as exc:
            self.errors += 1
            log.warning("telegram: no se pudo enviar el aviso urgente (%s)", exc)
            return False
        self.sent += 1
        return True

    def stop(self) -> None:
        self._stopping = True
        self._enqueue(None)

    def status(self) -> dict[str, Any]:
        return {
            "backend": "telegram",
            "connected": self._connected,
            "polling": self._polling(),
            "queued": self._queue.qsize(),
            "sent": self.sent,
            "errors": self.errors,
            "dropped": self.dropped,
            "commands": self.commands,
            "polling_errors": self.polling_errors,
            "reconnects": self.reconnects,
        }

    async def run(self) -> None:
        try:
            if not await self._connect_with_retries():
                return
            await self._drain()
        finally:
            await self._disconnect()

    # ------------------------------------------------------------- cola

    def _enqueue(self, item: QueueItem) -> None:
        while True:
            try:
                self._queue.put_nowait(item)
                return
            except asyncio.QueueFull:
                oldest = self._queue.get_nowait()
                if oldest is None:  # el centinela no se descarta: va detrás del nuevo
                    self._queue.put_nowait(item)
                    item = None
                    continue
                self.dropped += 1
                log.warning("telegram: cola llena, se descarta el aviso más viejo")

    async def _drain(self) -> None:
        while True:
            try:
                item = await asyncio.wait_for(self._queue.get(), self._poll_check_s)
            except TimeoutError:
                await self._check_polling()
                continue
            if item is None:
                return
            text, silent = item
            await self._deliver(text, silent)

    async def _deliver(self, text: str, silent: bool) -> None:
        for _attempt in range(2):
            try:
                await asyncio.wait_for(self._send(text, silent), self._send_timeout_s)
            except RetryAfter as exc:
                await self._pause(_retry_after_seconds(exc) + 1.0)
                continue
            except (TelegramError, OSError, TimeoutError) as exc:
                self.errors += 1
                log.warning("telegram: no se pudo enviar (%s)", exc)
                return
            self.sent += 1
            return
        self.errors += 1
        log.warning("telegram: rate limit persistente, aviso descartado")

    async def _send(self, text: str, silent: bool) -> None:
        if self.sender is not None:
            await self.sender(text, silent)
            return
        await self._app.bot.send_message(
            chat_id=self._chat_id, text=text, disable_notification=silent
        )

    async def _pause(self, seconds: float) -> None:
        remaining = seconds
        while remaining > 0 and not self._stopping:
            chunk = min(remaining, 10.0)
            await self._sleep(chunk)
            remaining -= chunk

    # ------------------------------------------------------------- conexión

    async def _connect_with_retries(self) -> bool:
        backoff = self._backoff_s
        while not self._stopping:
            try:
                await self._connect()
            except (TelegramError, OSError, TimeoutError) as exc:
                self.errors += 1
                log.warning("telegram: sin conexion (%s); reintento en %.0f s", exc, backoff)
                await self._pause(backoff)
                backoff = min(backoff * 2, self._backoff_max_s)
                continue
            return True
        return False

    def _build_app(self) -> Any:
        app = Application.builder().token(self._token).rate_limiter(AIORateLimiter()).build()
        # Solo mensajes nuevos con texto: un mensaje editado o un post de canal no re-ejecuta
        # un `/pause` o un `si` viejo.
        app.add_handler(MessageHandler(filters.UpdateType.MESSAGE & filters.TEXT, self._on_update))
        return app

    def _polling(self) -> bool:
        app = self._app
        if app is None:
            return self._connected and self.sender is not None  # modo solo envío (tests)
        if self._app_factory is not None:
            return bool(app.updater.running)
        updater = getattr(app, "updater", None)
        return bool(updater is not None and updater.running)

    def _on_polling_error(self, error: TelegramError) -> None:
        """PTB reintenta el polling solo; acá se cuenta y se loguea sin el token."""
        self.polling_errors += 1
        log.warning("telegram: error en el polling (%s: %s)", type(error).__name__, error)

    async def _connect(self) -> None:
        if self._app is None and self.sender is not None and self._app_factory is None:
            self._connected = True  # sin Application: solo envío (tests)
            return
        if self._app is not None:
            app = self._app
        elif self._app_factory is not None:
            app = self._app_factory()
        else:
            app = self._build_app()
        try:
            await app.initialize()
            await app.updater.start_polling(
                drop_pending_updates=True, error_callback=self._on_polling_error
            )
            await app.start()
        except BaseException:
            await _shutdown_quietly(app)
            self._app = None
            raise
        self._app = app
        self._connected = True
        log.info("telegram: conectado")

    async def _check_polling(self) -> None:
        """Si el `Updater` dejó de correr con el proceso vivo, se reconecta (I5)."""
        if self._stopping or self._app is None or self._polling():
            return
        self.reconnects += 1
        log.warning("telegram: el polling se detuvo; reconectando")
        await self._disconnect()
        await self._connect_with_retries()

    async def _disconnect(self) -> None:
        app, self._app = self._app, None
        self._connected = False
        if app is None:
            return
        await _shutdown_quietly(app)

    # ------------------------------------------------------------- comandos

    def dispatch(self, chat_id: str, text: str) -> str | None:
        """Respuesta a un mensaje entrante, o `None` si el chat no está en la whitelist."""
        if str(chat_id) != self._chat_id:
            if chat_id not in self.ignored_chats:
                self.ignored_chats.add(chat_id)
                log.warning("telegram: mensaje de un chat no autorizado, ignorado")
            return None
        self.commands += 1
        if self._on_command is None:
            return f"tradingbot {__version__} recibio: {text}"
        try:
            return self._on_command(text)
        except Exception:  # un comando roto no tumba el bot ni expone internals al chat
            self.errors += 1
            log.exception("telegram: error atendiendo %r", text)
            return COMMAND_ERROR_REPLY

    async def _on_update(self, update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        chat = update.effective_chat
        if message is None or chat is None or not message.text:
            return
        reply = self.dispatch(str(chat.id), message.text)
        if reply is None:
            return
        try:
            await asyncio.wait_for(message.reply_text(truncate(reply)), self._send_timeout_s)
        except (TelegramError, OSError, TimeoutError) as exc:
            self.errors += 1
            log.warning("telegram: no se pudo responder (%s)", exc)


async def _shutdown_quietly(app: Any) -> None:
    """Para el updater, la app y libera el bot, en ese orden, sin propagar errores."""
    updater = getattr(app, "updater", None)
    if updater is not None and updater.running:
        with contextlib.suppress(Exception):
            await updater.stop()
    if app.running:
        with contextlib.suppress(Exception):
            await app.stop()
    with contextlib.suppress(Exception):
        await app.shutdown()


def _retry_after_seconds(exc: RetryAfter) -> float:
    # PTB 22 guarda un `timedelta` en `_retry_after` y el atributo público avisa deprecación
    # mientras devuelve `int`; se toma el interno si existe y el público como respaldo.
    value: Any = getattr(exc, "_retry_after", None)
    if value is None:
        value = exc.retry_after
    total = getattr(value, "total_seconds", None)
    return float(total()) if callable(total) else float(value)


async def run_smoke_test(
    token: str,
    chat_id: str,
    *,
    seconds: float = 30.0,
    sender: Sender | None = None,
    poll_s: float = 1.0,
) -> tuple[dict[str, Any], list[str]]:
    """Manda un mensaje de prueba y espera comandos durante `seconds`; devuelve status y textos.

    `tradingbot telegram-test`: valida token y `chat_id` antes de reiniciar el paper con Telegram.
    `sender` reemplaza al bot real en los tests.
    """
    received: list[str] = []

    def echo(text: str) -> str:
        received.append(text)
        return f"tradingbot {__version__} recibio: {text}"

    notifier = TelegramNotifier(
        token,
        chat_id,
        on_command=echo,
        startup_backoff_s=5.0,
        startup_backoff_max_s=5.0,
        sender=sender,
    )
    task = asyncio.create_task(notifier.run())
    notifier.notify(
        Notification(
            ts=0,
            category=Category.LIFECYCLE,
            text=(
                f"prueba de tradingbot {__version__} desde {socket.gethostname()}: "
                f"responde cualquier cosa en los proximos {seconds:.0f} s"
            ),
        )
    )
    waited = 0.0
    while waited < seconds and not received and not task.done():
        await asyncio.sleep(poll_s)
        waited += poll_s
    notifier.stop()
    with contextlib.suppress(Exception):
        await asyncio.wait_for(task, 15.0)
    return notifier.status(), received
