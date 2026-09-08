"""Indicadores técnicos propios, vectorizados, en `float64`.

Contrato común:
- Entrada: secuencias 1-D de velas **cerradas** en orden temporal; salida: `np.ndarray` float64
  de la misma longitud, con `NaN` durante el warmup. El índice `i` de la salida depende solo de
  las entradas `[0, i]` (sin lookahead por construcción).
- Semillas compatibles con TA-Lib (modo de compatibilidad por defecto): las medias exponenciales
  arrancan con la SMA de los primeros `n` valores; RSI/ATR/ADX usan el suavizado de Wilder
  (`α = 1/n`); el ADX reproduce el algoritmo de `ta_ADX.c` (lookback `2n − 1`). Así los tests
  comparan contra TA-Lib desde el primer valor válido y no solo tras un burn-in.
- Este es el único lugar del proyecto donde el dinero vive en float (ADR-0003); la conversión
  Decimal → float ocurre al construir los arrays en `strategy/`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple

import numpy as np
import pandas as pd
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
ArrayLike = Sequence[float] | FloatArray


def as_float_array(values: ArrayLike, name: str = "values") -> FloatArray:
    """Convierte a `float64` 1-D; `Decimal` y escalares de numpy pasan por `float()`."""
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        msg = f"{name} debe ser 1-D, recibido ndim={array.ndim}"
        raise ValueError(msg)
    return array


def _check_period(period: int, minimum: int = 1, name: str = "period") -> None:
    if isinstance(period, bool) or not isinstance(period, int) or period < minimum:
        msg = f"{name} debe ser un entero >= {minimum}, recibido {period!r}"
        raise ValueError(msg)


def _same_length(*arrays: FloatArray) -> int:
    lengths = {a.size for a in arrays}
    if len(lengths) != 1:
        msg = f"las series deben tener la misma longitud, recibidas {sorted(lengths)}"
        raise ValueError(msg)
    return lengths.pop()


def _seeded_ewm(x: FloatArray, period: int, alpha: float) -> FloatArray:
    """Media exponencial sembrada con la SMA de los primeros `period` valores válidos.

    Tolera `NaN` iniciales (p. ej. la línea MACD o el true range): la semilla se calcula desde el
    primer valor válido. `NaN` intercalados después de ese punto son un error de datos.
    """
    n = x.size
    out = np.full(n, np.nan)
    valid = np.flatnonzero(~np.isnan(x))
    if valid.size == 0:
        return out
    start = int(valid[0])
    seed_index = start + period - 1
    if seed_index >= n:
        return out
    window = x[start : seed_index + 1]
    if np.isnan(window).any() or np.isnan(x[seed_index:]).any():
        msg = "NaN intercalados en la serie después del primer valor válido"
        raise ValueError(msg)
    tail = x[seed_index:].copy()
    tail[0] = window.mean()
    out[seed_index:] = pd.Series(tail).ewm(alpha=alpha, adjust=False).mean().to_numpy()
    return out


# ------------------------------------------------------------------ medias


def sma(values: ArrayLike, period: int) -> FloatArray:
    """Media móvil simple. Válida desde el índice `period − 1`."""
    _check_period(period)
    x = as_float_array(values)
    return pd.Series(x).rolling(period).mean().to_numpy(dtype=np.float64)


def ema(values: ArrayLike, period: int) -> FloatArray:
    """Media exponencial `α = 2/(n+1)` sembrada con SMA(n). Válida desde `period − 1`."""
    _check_period(period)
    return _seeded_ewm(as_float_array(values), period, 2.0 / (period + 1))


def wilder_smooth(values: ArrayLike, period: int) -> FloatArray:
    """Suavizado de Wilder (`α = 1/n`) sembrado con SMA(n). Base de RSI, ATR y ADX."""
    _check_period(period)
    return _seeded_ewm(as_float_array(values), period, 1.0 / period)


# ------------------------------------------------------------------ osciladores


def rsi(values: ArrayLike, period: int = 14) -> FloatArray:
    """RSI de Wilder. Válido desde el índice `period` (necesita `period` variaciones)."""
    _check_period(period, 2)
    x = as_float_array(values)
    out = np.full(x.size, np.nan)
    if x.size < period + 1:
        return out
    diff = np.diff(x)
    gains = np.where(diff > 0, diff, 0.0)
    losses = np.where(diff < 0, -diff, 0.0)
    avg_gain = _seeded_ewm(gains, period, 1.0 / period)
    avg_loss = _seeded_ewm(losses, period, 1.0 / period)
    total = avg_gain + avg_loss
    with np.errstate(divide="ignore", invalid="ignore"):
        value = np.where(total > 0, 100.0 * avg_gain / total, 0.0)
    value[np.isnan(avg_gain)] = np.nan
    out[1:] = value
    return out


class MacdResult(NamedTuple):
    macd: FloatArray
    signal: FloatArray
    hist: FloatArray


def macd(values: ArrayLike, fast: int = 12, slow: int = 26, signal: int = 9) -> MacdResult:
    """MACD con las semillas de TA-Lib.

    Las dos EMAs se siembran en el índice `slow − 1` (la rápida con la SMA de los últimos
    `fast` valores hasta ahí), y la señal con la SMA de las primeras `signal` diferencias.
    Las tres salidas son válidas desde `slow − 1 + signal − 1`.
    """
    _check_period(fast)
    _check_period(slow)
    _check_period(signal)
    if fast >= slow:
        msg = f"fast ({fast}) debe ser menor que slow ({slow})"
        raise ValueError(msg)
    x = as_float_array(values)
    slow_ema = _seeded_ewm(x, slow, 2.0 / (slow + 1))
    masked = x.copy()
    masked[: slow - fast] = np.nan
    fast_ema = _seeded_ewm(masked, fast, 2.0 / (fast + 1))
    line = fast_ema - slow_ema
    signal_line = _seeded_ewm(line, signal, 2.0 / (signal + 1))
    valid_from = min(slow - 1 + signal - 1, x.size)
    line[:valid_from] = np.nan
    hist = line - signal_line
    return MacdResult(macd=line, signal=signal_line, hist=hist)


# ------------------------------------------------------------------ volatilidad y tendencia


def true_range(high: ArrayLike, low: ArrayLike, close: ArrayLike) -> FloatArray:
    """True range: `max(h−l, |h−c₋₁|, |l−c₋₁|)`. El índice 0 es `NaN` (sin cierre previo)."""
    hi, lo, cl = (
        as_float_array(high, "high"),
        as_float_array(low, "low"),
        as_float_array(close, "close"),
    )
    n = _same_length(hi, lo, cl)
    out = np.full(n, np.nan)
    if n < 2:
        return out
    prev_close = cl[:-1]
    out[1:] = np.maximum(
        hi[1:] - lo[1:], np.maximum(np.abs(hi[1:] - prev_close), np.abs(lo[1:] - prev_close))
    )
    return out


def atr(high: ArrayLike, low: ArrayLike, close: ArrayLike, period: int = 14) -> FloatArray:
    """ATR de Wilder sobre el true range. Válido desde el índice `period`."""
    _check_period(period)
    return _seeded_ewm(true_range(high, low, close), period, 1.0 / period)


def adx(high: ArrayLike, low: ArrayLike, close: ArrayLike, period: int = 14) -> FloatArray:
    """ADX con el algoritmo exacto de TA-Lib (`ta_ADX.c`). Válido desde `2·period − 1`.

    Sumas de Wilder de +DM, −DM y TR: las primeras `period − 1` variaciones se acumulan, las
    siguientes `period` se suavizan y promedian su DX para sembrar el ADX. Casos de borde
    (TR acumulado 0 o DI⁺ + DI⁻ = 0, imposibles con datos reales) no actualizan el valor.
    """
    _check_period(period, 2)
    hi, lo, cl = (
        as_float_array(high, "high"),
        as_float_array(low, "low"),
        as_float_array(close, "close"),
    )
    n = _same_length(hi, lo, cl)
    out = np.full(n, np.nan)
    first_index = 2 * period - 1
    if n <= first_index:
        return out

    up = hi[1:] - hi[:-1]
    down = lo[:-1] - lo[1:]
    plus_dm = np.where((up > 0) & (up > down), up, 0.0)
    minus_dm = np.where((down > 0) & (down > up), down, 0.0)
    tr = true_range(hi, lo, cl)[1:]
    # `plus_dm[k]`, `minus_dm[k]`, `tr[k]` corresponden a la vela de precio `k + 1`.

    prev_plus = float(plus_dm[: period - 1].sum())
    prev_minus = float(minus_dm[: period - 1].sum())
    prev_tr = float(tr[: period - 1].sum())

    def step(price_index: int) -> float | None:
        nonlocal prev_plus, prev_minus, prev_tr
        k = price_index - 1
        prev_plus = prev_plus - prev_plus / period + plus_dm[k]
        prev_minus = prev_minus - prev_minus / period + minus_dm[k]
        prev_tr = prev_tr - prev_tr / period + tr[k]
        # TA-Lib compara con TA_IS_ZERO (|x| < 1e-8); con precios ≥ 1e-4 es equivalente a == 0.
        if prev_tr == 0.0:
            return None
        plus_di = 100.0 * prev_plus / prev_tr
        minus_di = 100.0 * prev_minus / prev_tr
        total = plus_di + minus_di
        if total == 0.0:
            return None
        return float(100.0 * abs(minus_di - plus_di) / total)

    sum_dx = 0.0
    for i in range(period, first_index + 1):
        dx = step(i)
        if dx is not None:
            sum_dx += dx
    prev_adx = sum_dx / period
    out[first_index] = prev_adx
    for i in range(first_index + 1, n):
        dx = step(i)
        if dx is not None:
            prev_adx = (prev_adx * (period - 1) + dx) / period
        out[i] = prev_adx
    return out


class BollingerBands(NamedTuple):
    upper: FloatArray
    middle: FloatArray
    lower: FloatArray


def bbands(
    values: ArrayLike, period: int = 20, dev_up: float = 2.0, dev_down: float = 2.0
) -> BollingerBands:
    """Bandas de Bollinger sobre SMA con desvío poblacional (`ddof = 0`, como TA-Lib)."""
    _check_period(period, 2)
    x = as_float_array(values)
    series = pd.Series(x)
    middle = series.rolling(period).mean().to_numpy(dtype=np.float64)
    std = series.rolling(period).std(ddof=0).to_numpy(dtype=np.float64)
    return BollingerBands(upper=middle + dev_up * std, middle=middle, lower=middle - dev_down * std)


def highest(values: ArrayLike, period: int) -> FloatArray:
    """Máximo móvil de las últimas `period` velas (inclusive). Válido desde `period − 1`."""
    _check_period(period)
    return pd.Series(as_float_array(values)).rolling(period).max().to_numpy(dtype=np.float64)


def lowest(values: ArrayLike, period: int) -> FloatArray:
    """Mínimo móvil de las últimas `period` velas (inclusive). Válido desde `period − 1`."""
    _check_period(period)
    return pd.Series(as_float_array(values)).rolling(period).min().to_numpy(dtype=np.float64)


# ------------------------------------------------------------------ cruces


def _pair_for_cross(a: ArrayLike, b: ArrayLike | float) -> tuple[FloatArray, FloatArray]:
    x = as_float_array(a, "a")
    y = np.asarray(b, dtype=np.float64)
    if y.ndim == 0:
        y = np.full(x.size, float(y))
    elif y.ndim != 1:
        msg = f"b debe ser escalar o 1-D, recibido ndim={y.ndim}"
        raise ValueError(msg)
    _same_length(x, y)
    return x, y


def cross_above(a: ArrayLike, b: ArrayLike | float) -> BoolArray:
    """True en `i` si `a[i−1] <= b[i−1]` y `a[i] > b[i]`. `NaN` nunca cruza."""
    x, y = _pair_for_cross(a, b)
    out = np.zeros(x.size, dtype=np.bool_)
    if x.size >= 2:
        out[1:] = (x[:-1] <= y[:-1]) & (x[1:] > y[1:])
    return out


def cross_below(a: ArrayLike, b: ArrayLike | float) -> BoolArray:
    """True en `i` si `a[i−1] >= b[i−1]` y `a[i] < b[i]`. `NaN` nunca cruza."""
    x, y = _pair_for_cross(a, b)
    out = np.zeros(x.size, dtype=np.bool_)
    if x.size >= 2:
        out[1:] = (x[:-1] >= y[:-1]) & (x[1:] < y[1:])
    return out
