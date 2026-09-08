"""Reloj del motor: real en paper/live, simulado en backtest. Siempre ms epoch UTC."""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    def now_ms(self) -> int: ...


class RealClock:
    """Hora del sistema corregida por `offset_ms` (reloj del exchange − reloj local).

    El adapter de exchange (Fase 2) mide el offset con `fetch_time` y lo actualiza con
    `set_offset`; así el `Engine` nunca decide cierres de vela con la hora local cruda.
    """

    def __init__(self, offset_ms: int = 0) -> None:
        self._offset_ms = offset_ms

    @property
    def offset_ms(self) -> int:
        return self._offset_ms

    def set_offset(self, offset_ms: int) -> None:
        self._offset_ms = offset_ms

    def now_ms(self) -> int:
        return int(time.time() * 1000) + self._offset_ms


class SimClock:
    """Reloj controlado por el backtest. Solo avanza; retroceder es un bug."""

    def __init__(self, start_ms: int = 0) -> None:
        if start_ms < 0:
            msg = f"start_ms negativo: {start_ms}"
            raise ValueError(msg)
        self._now = start_ms

    def now_ms(self) -> int:
        return self._now

    def advance_to(self, ts_ms: int) -> None:
        if ts_ms < self._now:
            msg = f"el reloj simulado no retrocede: {ts_ms} < {self._now}"
            raise ValueError(msg)
        self._now = ts_ms

    def advance(self, delta_ms: int) -> None:
        if delta_ms < 0:
            msg = f"delta negativo: {delta_ms}"
            raise ValueError(msg)
        self._now += delta_ms
