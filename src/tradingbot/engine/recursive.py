"""Estado de indicadores por par; checkpoint independiente de Strategy (ADR-0014)."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from tradingbot.domain.candle import Candle
from tradingbot.domain.errors import DataError
from tradingbot.indicators.core import FloatArray
from tradingbot.strategy.base import OhlcvArrays, Strategy


class RecursiveSeries:
    def __init__(
        self,
        strategy: Strategy,
        candles: Sequence[Candle],
        checkpoint: Mapping[str, Any] | None = None,
    ) -> None:
        self.strategy = strategy
        self.fingerprint = hashlib.sha256(
            (strategy.name + strategy.params.model_dump_json()).encode()
        ).hexdigest()
        self.state: dict[str, Any] = {}
        self.before_last: dict[str, Any] = {}
        self.last_time: int | None = None
        self.values: dict[int, dict[str, float]] = {}
        if checkpoint is not None:
            if checkpoint.get("version") != 1 or checkpoint.get("fingerprint") != self.fingerprint:
                raise DataError("checkpoint de indicadores incompatible con estrategia/parámetros")
            self.state = dict(checkpoint["state"])
            self.before_last = dict(checkpoint["before_last"])
            self.last_time = int(checkpoint["last_time"])
            self.values = {
                int(t): {k: math.nan if v is None else float(v) for k, v in vs.items()}
                for t, vs in checkpoint["values"].items()
            }
            if not candles or candles[-1].open_time != self.last_time:
                raise DataError("checkpoint de indicadores desalineado con warmup")
            if any(c.open_time not in self.values for c in candles):
                raise DataError("checkpoint no cubre la ventana recuperada")
        else:
            # Valida también timeframe/bars_per_day antes de construir estado.
            if candles:
                strategy.compute_indicators(OhlcvArrays.from_candles(candles[:1]))
            for candle in candles:
                self.update(candle)

    def update(self, candle: Candle) -> None:
        if self.last_time is not None and candle.open_time < self.last_time:
            raise DataError("indicador recursivo recibió una vela anterior")
        if candle.open_time == self.last_time:
            previous = self.before_last
        else:
            previous = self.state
            self.before_last = dict(self.state)
        a = OhlcvArrays.from_candles([candle])
        self.state, values = self.strategy.indicator_step(
            previous, float(a.high[0]), float(a.low[0]), float(a.close[0])
        )
        self.values[candle.open_time] = values
        self.last_time = candle.open_time

    def arrays(self, candles: Sequence[Candle]) -> dict[str, FloatArray]:
        times = {c.open_time for c in candles}
        self.values = {t: v for t, v in self.values.items() if t in times}
        names = next(iter(self.values.values())).keys()
        return {
            key: np.array([self.values[c.open_time][key] for c in candles], dtype=np.float64)
            for key in names
        }

    def checkpoint(self) -> dict[str, Any]:
        if self.last_time is None:
            raise DataError("no hay estado recursivo para persistir")
        result = {
            "version": 1,
            "fingerprint": self.fingerprint,
            "state": self.state,
            "before_last": self.before_last,
            "last_time": self.last_time,
            "values": {
                str(t): {k: v if math.isfinite(v) else None for k, v in vs.items()}
                for t, vs in self.values.items()
            },
        }
        # Corta referencias y exige JSON sin NaN: el checkpoint no muta con la próxima vela.
        return dict(json.loads(json.dumps(result, allow_nan=False)))
