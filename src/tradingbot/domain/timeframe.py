"""Timeframes de velas y aritmética de tiempo.

Todo timestamp es `int` en milisegundos epoch UTC. Una vela se identifica por su `open_time`,
alineado a múltiplos del timeframe desde epoch (así alinea Binance sus klines de 1m a 1d).
"""

from __future__ import annotations

from enum import StrEnum

_MINUTE_MS = 60_000
_HOUR_MS = 60 * _MINUTE_MS
_DAY_MS = 24 * _HOUR_MS


class Timeframe(StrEnum):
    """Duración de cada vela, con el nombre que usa Binance/ccxt."""

    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

    @property
    def ms(self) -> int:
        """Duración en milisegundos."""
        return _DURATIONS_MS[self]

    def to_ms(self) -> int:
        """Alias explícito de `ms`."""
        return self.ms

    def floor(self, ts_ms: int) -> int:
        """`open_time` de la vela que contiene `ts_ms`."""
        _check_ts(ts_ms)
        return ts_ms - ts_ms % self.ms

    def close_time(self, open_time: int) -> int:
        """Último milisegundo de la vela que abre en `open_time` (inclusive)."""
        self.check_aligned(open_time)
        return open_time + self.ms - 1

    def next_close(self, ts_ms: int) -> int:
        """Primer instante en que la vela que contiene `ts_ms` ya está cerrada.

        Coincide con el `open_time` de la vela siguiente.
        """
        return self.floor(ts_ms) + self.ms

    def is_closed(self, open_time: int, now_ms: int) -> bool:
        """True si la vela que abre en `open_time` ya cerró en el instante `now_ms`."""
        self.check_aligned(open_time)
        return now_ms >= open_time + self.ms

    def is_aligned(self, ts_ms: int) -> bool:
        """True si `ts_ms` es un `open_time` válido para este timeframe."""
        return ts_ms >= 0 and ts_ms % self.ms == 0

    def check_aligned(self, ts_ms: int) -> None:
        """Lanza `ValueError` si `ts_ms` no es un `open_time` válido."""
        if not self.is_aligned(ts_ms):
            msg = f"{ts_ms} no está alineado a velas de {self.value}"
            raise ValueError(msg)

    def candles_per_day(self) -> int:
        """Cantidad de velas por día UTC (para anualizar métricas)."""
        return _DAY_MS // self.ms

    @classmethod
    def parse(cls, value: str) -> Timeframe:
        """Convierte '4h' → Timeframe.H4; acepta también el nombre del miembro ('H4')."""
        text = value.strip()
        try:
            return cls(text.lower())
        except ValueError:
            pass
        try:
            return cls[text.upper()]
        except KeyError as exc:
            valid = ", ".join(tf.value for tf in cls)
            msg = f"timeframe inválido {value!r}; válidos: {valid}"
            raise ValueError(msg) from exc


_DURATIONS_MS: dict[Timeframe, int] = {
    Timeframe.M1: _MINUTE_MS,
    Timeframe.M5: 5 * _MINUTE_MS,
    Timeframe.M15: 15 * _MINUTE_MS,
    Timeframe.M30: 30 * _MINUTE_MS,
    Timeframe.H1: _HOUR_MS,
    Timeframe.H4: 4 * _HOUR_MS,
    Timeframe.D1: _DAY_MS,
}


def _check_ts(ts_ms: int) -> None:
    if ts_ms < 0:
        msg = f"timestamp negativo: {ts_ms}"
        raise ValueError(msg)
