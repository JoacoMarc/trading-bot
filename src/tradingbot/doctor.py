"""Chequeos de entorno para `tradingbot doctor`.

Cada chequeo devuelve un `CheckResult` y nunca imprime valores de secretos, solo nombres.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

MAX_CLOCK_OFFSET_MS = 1000
MIN_PYTHON = (3, 12)
SECRET_VARS = (
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "ANTHROPIC_API_KEY",
)


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Resultado de un chequeo individual."""

    name: str
    ok: bool
    detail: str


def _now_ms() -> int:
    return int(time.time() * 1000)


def check_python(version_info: tuple[int, int] | None = None) -> CheckResult:
    """Verifica la versión mínima de Python."""
    current = version_info or (sys.version_info.major, sys.version_info.minor)
    ok = current >= MIN_PYTHON
    detail = f"{current[0]}.{current[1]} (mínimo {MIN_PYTHON[0]}.{MIN_PYTHON[1]})"
    return CheckResult("python", ok, detail)


def check_env(environ: Mapping[str, str] | None = None) -> CheckResult:
    """Informa qué variables de secretos están definidas, sin mostrar sus valores."""
    env = os.environ if environ is None else environ
    present = [name for name in SECRET_VARS if env.get(name)]
    missing = [name for name in SECRET_VARS if not env.get(name)]
    detail = (
        f"definidas: {', '.join(present) or 'ninguna'}; "
        f"sin definir: {', '.join(missing) or 'ninguna'}"
    )
    return CheckResult("env", True, detail)


def check_binance(
    fetch_server_time_ms: Callable[[], int],
    now_ms: Callable[[], int] = _now_ms,
    max_offset_ms: int = MAX_CLOCK_OFFSET_MS,
) -> list[CheckResult]:
    """Verifica conectividad con Binance y el desfase del reloj local.

    El offset se mide contra el punto medio de la ida y vuelta. Binance rechaza órdenes
    firmadas con más de ~1000 ms de adelanto respecto de su reloj (error -1021).
    """
    try:
        t0 = now_ms()
        server_ms = fetch_server_time_ms()
        t1 = now_ms()
    except Exception as exc:  # doctor reporta cualquier falla de red, no la propaga
        detail = f"sin conexión con Binance: {type(exc).__name__}: {exc}"
        return [CheckResult("binance", False, detail)]

    offset_ms = server_ms - (t0 + t1) // 2
    clock_ok = abs(offset_ms) <= max_offset_ms
    return [
        CheckResult("binance", True, f"fetch_time ok, ida y vuelta {t1 - t0} ms"),
        CheckResult(
            "reloj",
            clock_ok,
            f"offset {offset_ms:+d} ms vs Binance (máximo ±{max_offset_ms} ms)",
        ),
    ]


def fetch_binance_server_time_ms() -> int:
    """Consulta la hora del servidor de Binance (endpoint público, sin claves)."""
    import ccxt  # import local: ccxt tarda en importar y doctor debe arrancar rápido

    exchange = ccxt.binance({"enableRateLimit": True, "timeout": 10_000})
    return int(exchange.fetch_time())


def run_all(
    fetch_server_time_ms: Callable[[], int] = fetch_binance_server_time_ms,
) -> list[CheckResult]:
    """Corre todos los chequeos y devuelve sus resultados en orden."""
    return [check_python(), check_env(), *check_binance(fetch_server_time_ms)]
