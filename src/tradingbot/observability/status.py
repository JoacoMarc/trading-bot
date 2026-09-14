"""`logs/status.json`: foto del bot escrita de forma atómica en cada ciclo (ADR-0011).

La leen el `HEALTHCHECK` de Docker (`tradingbot status --check`), `tradingbot status` y la skill
`/paper-status`; ninguno abre la DB. Un heartbeat más viejo que `2 × timeframe + gracia` significa
que el proceso no está procesando cierres.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tradingbot.persistence.files import atomic_write_text

STATUS_VERSION = 1
DEFAULT_GRACE_MS = 300_000


def _iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


class StatusWriter:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, payload: Mapping[str, Any], *, heartbeat_ts: int) -> dict[str, Any]:
        """Agrega versión y heartbeat y escribe el archivo entero de una vez."""
        data: dict[str, Any] = {
            **payload,  # el heartbeat y la versión de abajo siempre ganan
            "version": STATUS_VERSION,
            "heartbeat_ts": heartbeat_ts,
            "heartbeat_utc": _iso(heartbeat_ts),
        }
        atomic_write_text(
            self.path, json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n"
        )
        return data


def read_status(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return dict(loaded) if isinstance(loaded, dict) else None


def heartbeat_age_ms(status: Mapping[str, Any], now_ms: int) -> int | None:
    raw = status.get("heartbeat_ts")
    if raw is None:
        return None
    try:
        return max(now_ms - int(raw), 0)
    except (TypeError, ValueError):
        return None


def is_stale(status: Mapping[str, Any], now_ms: int, *, grace_ms: int = DEFAULT_GRACE_MS) -> bool:
    """True si el heartbeat es más viejo que `2 × timeframe + gracia` o no se puede leer."""
    age = heartbeat_age_ms(status, now_ms)
    if age is None:
        return True
    try:
        timeframe_ms = int(status["timeframe_ms"])
    except (KeyError, TypeError, ValueError):
        return True
    return age > 2 * timeframe_ms + grace_ms
