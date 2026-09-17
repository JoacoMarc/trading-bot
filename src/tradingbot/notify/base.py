"""Puerto `Notifier` (ADR-0012): avisos ya renderizados en texto plano que nunca frenan al bot.

`Notification` la arma la sesión (categoría + texto); el `Notifier` decide si la manda y cómo según
`NotifyConfig.events` (`on` con sonido, `silent` sin sonido, `off` no se manda). `notify()` es
síncrono y no bloquea: encola o loguea. `run()`/`stop()` son el ciclo de vida para correr como
tarea auxiliar de la sesión de paper. `LogNotifier` es el default en todos los modos.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from tradingbot.domain.pair import Pair

log = logging.getLogger(__name__)


class Level(StrEnum):
    ON = "on"  # aviso con sonido
    SILENT = "silent"  # aviso sin sonido
    OFF = "off"  # no se manda


class Category(StrEnum):
    ENTRY = "entry"  # posición abierta
    EXIT = "exit"  # trade cerrado por señal, flatten o riesgo
    STOP = "stop"  # trade cerrado por stop o trailing
    STUCK = "stuck"  # salida trabada por filtros del exchange
    PROTECTION = "protection"  # circuit breaker, pérdida diaria, kill switch, filtro de mercado
    REJECTION = "rejection"  # entrada rechazada por riesgo o por el broker
    FEED = "feed"  # velas tardías, huecos, reintentos del exchange
    ERROR = "error"  # tareas caídas, watchdog, fallas de persistencia
    LIFECYCLE = "lifecycle"  # arranque, parada, reanudación
    DAILY = "daily"  # resumen diario


DEFAULT_LEVELS: dict[Category, Level] = {
    Category.ENTRY: Level.ON,
    Category.EXIT: Level.ON,
    Category.STOP: Level.ON,
    Category.STUCK: Level.ON,
    Category.PROTECTION: Level.ON,
    Category.REJECTION: Level.SILENT,
    Category.FEED: Level.SILENT,
    Category.ERROR: Level.ON,
    Category.LIFECYCLE: Level.ON,
    Category.DAILY: Level.ON,
}

TELEGRAM_TEXT_MAX = 4096


def coerce_level(value: object) -> object:
    """YAML 1.1 lee `on`/`off` como booleanos: se vuelven a su nivel antes de validar."""
    if value is True:
        return Level.ON.value
    if value is False:
        return Level.OFF.value
    return value


def resolve_level(levels: Mapping[Category, Level], category: Category) -> Level:
    return levels.get(category, DEFAULT_LEVELS.get(category, Level.ON))


@dataclass(frozen=True, slots=True)
class Notification:
    ts: int
    category: Category
    text: str
    pair: Pair | None = None
    delivery_id: str | None = None


class Notifier(Protocol):
    def notify(self, note: Notification) -> None:
        """Encola o loguea. Nunca bloquea ni lanza."""
        ...

    async def run(self) -> None:
        """Corre hasta `stop()`; una excepción acá no debe tumbar el ciclo de velas."""
        ...

    def stop(self) -> None: ...

    async def send_now(self, text: str, *, timeout_s: float = 5.0) -> bool:
        """Envío directo y acotado, sin cola: para avisar antes de que el proceso muera."""
        ...

    def status(self) -> dict[str, Any]:
        """Contadores serializables para `status.json` (`backend`, `sent`, `errors`, ...)."""
        ...


class LogNotifier:
    """Escribe cada aviso al log; `run()` solo espera a `stop()`."""

    def __init__(self, levels: Mapping[Category, Level] | None = None, *, prefix: str = "") -> None:
        self._prefix = prefix
        self._levels = dict(DEFAULT_LEVELS if levels is None else levels)
        self._stopped = False
        self._sent = 0
        self._wake: asyncio.Event | None = None

    def notify(self, note: Notification) -> None:
        if resolve_level(self._levels, note.category) is Level.OFF:
            return
        self._sent += 1
        log.info("[%s] %s%s", note.category.value, self._prefix, note.text)

    async def send_now(self, text: str, *, timeout_s: float = 5.0) -> bool:
        self._sent += 1
        log.warning("[urgente] %s%s", self._prefix, text)
        return True

    async def run(self) -> None:
        self._wake = asyncio.Event()
        if self._stopped:
            return
        await self._wake.wait()

    def stop(self) -> None:
        self._stopped = True
        if self._wake is not None:
            self._wake.set()

    def status(self) -> dict[str, Any]:
        return {"backend": "log", "sent": self._sent, "errors": 0, "dropped": 0, "queued": 0}


def truncate(text: str, limit: int = TELEGRAM_TEXT_MAX) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
