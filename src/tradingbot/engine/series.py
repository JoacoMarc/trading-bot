"""Series por par que el `Engine` entrega a la estrategia.

`PrecomputedSeries` (backtest): arrays e indicadores calculados una vez sobre warmup + rango;
el contexto de cada vela es una vista hasta su índice. `RollingSeries` (paper/live) recomputa los
indicadores sobre la ventana de warmup + velas nuevas en cada cierre, con el mismo protocolo;
`validation/equivalence` garantiza que ambas den lo mismo.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from tradingbot.domain.candle import Bar, Candle
from tradingbot.domain.errors import DataError
from tradingbot.domain.pair import Pair
from tradingbot.engine.recursive import RecursiveSeries
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
        checkpoints: Mapping[str, Any] | None = None,
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
        self._recursive: dict[Pair, RecursiveSeries] = {}
        if strategy.recursive_indicators:
            for pair, history in self._candles.items():
                saved = (checkpoints or {}).get(pair.symbol)
                if saved is None:
                    self._recursive[pair] = RecursiveSeries(strategy, history)
                    continue
                previous = [Candle.model_validate(c) for c in saved["history"]]
                state = RecursiveSeries(strategy, previous, saved)
                # No revisar decisiones pasadas con velas corregidas/publicadas tarde.
                # Recuperar únicamente el sufijo que este par aún no había observado.
                catchup = [c for c in history if c.open_time > previous[-1].open_time]
                for candle in catchup:
                    state.update(candle)
                recovered = [*previous, *catchup][-window:]
                self._candles[pair] = recovered
                state.arrays(recovered)
                self._recursive[pair] = state

    def checkpoint(self) -> dict[str, Any]:
        return {
            p.symbol: {
                **state.checkpoint(),
                "history": [c.model_dump(mode="json") for c in self._candles[p]],
            }
            for p, state in self._recursive.items()
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
        if self._strategy.recursive_indicators:
            state = self._recursive.get(pair)
            if state is None:
                state = RecursiveSeries(self._strategy, history[:-1])
                self._recursive[pair] = state
            state.update(candle)
            return SeriesAt(arrays, state.arrays(history), len(history) - 1)
        return SeriesAt(arrays, self._strategy.compute_indicators(arrays), len(history) - 1)
