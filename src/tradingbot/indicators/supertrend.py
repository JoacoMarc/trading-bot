"""Supertrend recursivo con estado JSON, semillas explícitas y sin estado global."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np

from tradingbot.indicators.core import ArrayLike, FloatArray, as_float_array


def supertrend_step(
    state: Mapping[str, Any], high: float, low: float, close: float, period: int, multiplier: float
) -> tuple[dict[str, Any], dict[str, float]]:
    if period < 2 or not math.isfinite(multiplier) or multiplier <= 0:
        raise ValueError("período/multiplicador inválidos")
    if not all(math.isfinite(x) for x in (high, low, close)) or not low <= close <= high:
        raise ValueError("OHLC inválido para Supertrend")
    out = dict(state)
    previous = out.get("close")
    out["close"] = close
    if previous is not None:
        tr = max(high - low, abs(high - previous), abs(low - previous))
        for key, n in (("atr", period), ("atr_stop", 14)):
            count = int(out.get(key + "_count", 0)) + 1
            out[key + "_count"] = min(count, n)
            value = out.get(key)
            if value is None:
                total = float(out.get(key + "_sum", 0.0)) + tr
                out[key + "_sum"] = total
                if count == n:
                    out[key] = total / n
            else:
                out[key] = (value * (n - 1) + tr) / n
    volatility = out.get("atr")
    if volatility is not None:
        bu, bl = (
            (high + low) / 2 + multiplier * volatility,
            (high + low) / 2 - multiplier * volatility,
        )
        if "direction" not in out:
            out.update(upper=bu, lower=bl, direction=-1)
        else:
            if previous is None:
                raise ValueError("checkpoint sin cierre previo")
            upper, lower = float(out["upper"]), float(out["lower"])
            out["upper"] = bu if bu < upper or previous > upper else upper
            out["lower"] = bl if bl > lower or previous < lower else lower
            if out["direction"] == -1 and close > out["upper"]:
                out["direction"] = 1
            elif out["direction"] == 1 and close < out["lower"]:
                out["direction"] = -1
        out["line"] = out["lower"] if out["direction"] == 1 else out["upper"]
    values = {
        key: float(out.get(key, math.nan))
        for key in ("line", "upper", "lower", "direction", "atr", "atr_stop")
    }
    return out, values


def supertrend(
    high: ArrayLike, low: ArrayLike, close: ArrayLike, period: int = 10, multiplier: float = 3.0
) -> dict[str, FloatArray]:
    hi, lo, cl = (as_float_array(x) for x in (high, low, close))
    if not (len(hi) == len(lo) == len(cl)):
        raise ValueError("series de distinto tamaño")
    result = {
        key: np.full(len(cl), np.nan)
        for key in ("line", "upper", "lower", "direction", "atr", "atr_stop")
    }
    state: dict[str, Any] = {}
    for i in range(len(cl)):
        state, values = supertrend_step(
            state, float(hi[i]), float(lo[i]), float(cl[i]), period, multiplier
        )
        for key, value in values.items():
            result[key][i] = value
    return result
