"""Feeds de mercado: emiten `Bar`s (todas las velas de un mismo cierre) al `Engine`.

`MarketFeed` es el puerto de ADR-0002. Acá vive `HistoricalFeed` (parquet → `Bar`); `LiveFeed`
llega en la Fase 7 con el mismo contrato.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Protocol

from tradingbot.data.store import ParquetStore
from tradingbot.domain.candle import Bar, Candle
from tradingbot.domain.errors import DataError, InsufficientWarmup
from tradingbot.domain.pair import Pair
from tradingbot.domain.timeframe import Timeframe


class MarketFeed(Protocol):
    """Fuente de `Bar`s cerrados, en orden temporal estricto."""

    @property
    def timeframe(self) -> Timeframe: ...

    @property
    def pairs(self) -> tuple[Pair, ...]: ...

    def warmup_bars(self) -> list[Bar]:
        """Bars anteriores al inicio, para que la estrategia arranque con indicadores válidos."""
        ...

    def __aiter__(self) -> AsyncIterator[Bar]: ...


class HistoricalFeed:
    """Reproduce velas guardadas como `Bar`s en `[start_ms, end_ms)`.

    - Precarga `warmup` velas por par antes de `start_ms`; si algún par no las tiene, falla con
      `InsufficientWarmup` al construirse (mejor que descubrirlo a mitad del backtest).
    - Tolera pares faltantes en un cierre: el `Bar` sale sin ese par.
    - `start_ms` se alinea hacia abajo al timeframe; `end_ms` es exclusivo sobre `open_time`
      (una vela que abre antes de `end_ms` entra aunque cierre después).
    """

    def __init__(
        self,
        store: ParquetStore,
        pairs: Sequence[Pair],
        timeframe: Timeframe,
        start_ms: int,
        end_ms: int,
        warmup: int = 0,
    ) -> None:
        if not pairs:
            msg = "HistoricalFeed necesita al menos un par"
            raise ValueError(msg)
        if warmup < 0:
            msg = f"warmup negativo: {warmup}"
            raise ValueError(msg)
        self._timeframe = timeframe
        self._pairs = tuple(sorted(set(pairs)))
        self._start_ms = timeframe.floor(start_ms)
        self._end_ms = end_ms
        if self._end_ms <= self._start_ms:
            msg = f"end_ms {end_ms} debe ser posterior a start_ms {start_ms}"
            raise ValueError(msg)
        self._warmup = warmup
        self._warmup_candles: dict[Pair, list[Candle]] = {}
        self._candles: dict[Pair, dict[int, Candle]] = {}
        self._load(store)

    # ------------------------------------------------------------- carga

    def _load(self, store: ParquetStore) -> None:
        for pair in self._pairs:
            # Sin cota inferior: si hay huecos reales dentro de la ventana de warmup, se toman las
            # `warmup` velas cerradas más recientes antes de `start`, aunque abarquen más tiempo.
            candles = store.read_candles(pair, self._timeframe, None, self._end_ms)
            before = [c for c in candles if c.open_time < self._start_ms]
            if len(before) < self._warmup:
                msg = (
                    f"{pair} {self._timeframe.value}: warmup de {self._warmup} velas antes de "
                    f"{self._start_ms}, disponibles {len(before)}"
                )
                raise InsufficientWarmup(msg)
            self._warmup_candles[pair] = (
                before[len(before) - self._warmup :] if self._warmup else []
            )
            self._candles[pair] = {c.open_time: c for c in candles if c.open_time >= self._start_ms}
        if not any(self._candles.values()):
            msg = (
                f"sin velas de {self._timeframe.value} en [{self._start_ms}, {self._end_ms}) "
                f"para {', '.join(p.symbol for p in self._pairs)}"
            )
            raise DataError(msg)

    # ------------------------------------------------------------- API

    @property
    def timeframe(self) -> Timeframe:
        return self._timeframe

    @property
    def pairs(self) -> tuple[Pair, ...]:
        return self._pairs

    @property
    def start_ms(self) -> int:
        return self._start_ms

    @property
    def end_ms(self) -> int:
        return self._end_ms

    @property
    def open_times(self) -> tuple[int, ...]:
        """Cierres a emitir: unión de los `open_time` de todos los pares, ordenada."""
        times: set[int] = set()
        for by_time in self._candles.values():
            times.update(by_time)
        return tuple(sorted(times))

    def __len__(self) -> int:
        return len(self.open_times)

    def warmup_candles(self, pair: Pair) -> list[Candle]:
        return list(self._warmup_candles[pair])

    def warmup_bars(self) -> list[Bar]:
        times: set[int] = set()
        for candles in self._warmup_candles.values():
            times.update(c.open_time for c in candles)
        by_pair = {
            pair: {c.open_time: c for c in candles}
            for pair, candles in self._warmup_candles.items()
        }
        return [self._bar_at(t, by_pair) for t in sorted(times)]

    def _bar_at(self, open_time: int, source: dict[Pair, dict[int, Candle]]) -> Bar:
        candles = {
            pair: by_time[open_time] for pair, by_time in source.items() if open_time in by_time
        }
        return Bar(timeframe=self._timeframe, open_time=open_time, candles=candles)

    def iter_bars(self) -> Iterator[Bar]:
        """Versión síncrona de la iteración (tests y herramientas)."""
        for open_time in self.open_times:
            yield self._bar_at(open_time, self._candles)

    async def __aiter__(self) -> AsyncIterator[Bar]:
        for bar in self.iter_bars():
            yield bar
