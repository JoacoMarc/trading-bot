"""Series por par que el `Engine` entrega a la estrategia.

`PrecomputedSeries` (backtest): arrays e indicadores calculados una vez sobre warmup + rango;
el contexto de cada vela es una vista hasta su índice. `RollingSeries` (paper/live) recomputa los
indicadores sobre la ventana de warmup + velas nuevas en cada cierre, con el mismo protocolo;
`validation/equivalence` garantiza que ambas den lo mismo.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from tradingbot.domain.candle import Bar, Candle
from tradingbot.domain.errors import DataError
from tradingbot.domain.pair import Pair
from tradingbot.indicators.core import FloatArray
from tradingbot.strategy.base import OhlcvArrays, Strategy


@dataclass(frozen=True, slots=True)
class SeriesAt:
    """Arrays completos del par, indicadores y el índice de la vela actual."""

    ohlcv: OhlcvArrays
    indicators: Mapping[str, FloatArray]
    index: int


class SeriesProvider(Protocol):
    @property
    def pairs(self) -> tuple[Pair, ...]: ...

    def at(self, pair: Pair, bar: Bar) -> SeriesAt | None:
        """Series del par posicionadas en la vela del `bar`; None si el par no está en el bar."""
        ...


class PrecomputedSeries:
    def __init__(
        self, strategy: Strategy, candles_by_pair: Mapping[Pair, Sequence[Candle]]
    ) -> None:
        self._arrays: dict[Pair, OhlcvArrays] = {}
        self._indicators: dict[Pair, dict[str, FloatArray]] = {}
        self._index_by_time: dict[Pair, dict[int, int]] = {}
        for pair, candles in candles_by_pair.items():
            if not candles:
                continue
            arrays = OhlcvArrays.from_candles(candles)
            self._arrays[pair] = arrays
            self._indicators[pair] = strategy.compute_indicators(arrays)
            self._index_by_time[pair] = {int(t): i for i, t in enumerate(arrays.open_time)}
        if not self._arrays:
            msg = "PrecomputedSeries necesita velas de al menos un par"
            raise DataError(msg)

    @property
    def pairs(self) -> tuple[Pair, ...]:
        return tuple(sorted(self._arrays))

    def arrays(self, pair: Pair) -> OhlcvArrays:
        return self._arrays[pair]

    def at(self, pair: Pair, bar: Bar) -> SeriesAt | None:
        candle = bar.get(pair)
        if candle is None or pair not in self._arrays:
            return None
        try:
            index = self._index_by_time[pair][candle.open_time]
        except KeyError as exc:
            msg = f"{pair}: la vela {candle.open_time} no está en la serie precomputada"
            raise DataError(msg) from exc
        return SeriesAt(self._arrays[pair], self._indicators[pair], index)


class RollingSeries:
    """Live: ventana rodante por par (warmup + velas nuevas), indicadores recomputados por cierre.

    `window` es cuántas velas se conservan (≥ warmup + 1). Una vela con el mismo `open_time` que
    la última reemplaza a la anterior (re-proceso idempotente); una anterior es un error de orden.
    """

    def __init__(
        self,
        strategy: Strategy,
        warmup_by_pair: Mapping[Pair, Sequence[Candle]],
        *,
        window: int,
    ) -> None:
        if window < 1:
            msg = f"window debe ser >= 1, recibido {window}"
            raise ValueError(msg)
        self._strategy = strategy
        self._window = window
        self._candles: dict[Pair, list[Candle]] = {
            pair: sorted(candles, key=lambda c: c.open_time)[-window:]
            for pair, candles in warmup_by_pair.items()
        }

    @property
    def pairs(self) -> tuple[Pair, ...]:
        return tuple(sorted(self._candles))

    def history(self, pair: Pair) -> list[Candle]:
        return list(self._candles.get(pair, []))

    def at(self, pair: Pair, bar: Bar) -> SeriesAt | None:
        candle = bar.get(pair)
        if candle is None:
            return None
        history = self._candles.setdefault(pair, [])
        if history and history[-1].open_time == candle.open_time:
            history[-1] = candle
        elif history and history[-1].open_time > candle.open_time:
            msg = (
                f"{pair}: vela {candle.open_time} anterior a la última conocida "
                f"{history[-1].open_time}"
            )
            raise DataError(msg)
        else:
            history.append(candle)
        if len(history) > self._window:
            del history[: len(history) - self._window]
        arrays = OhlcvArrays.from_candles(history)
        return SeriesAt(arrays, self._strategy.compute_indicators(arrays), len(history) - 1)
