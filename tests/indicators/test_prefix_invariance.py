"""Sin lookahead por construcción: `f(x[:k])` coincide con `f(x)[:k]` para todo indicador."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tradingbot.indicators import (
    FloatArray,
    adx,
    atr,
    bbands,
    cross_above,
    ema,
    highest,
    lowest,
    macd,
    rsi,
    sma,
    wilder_smooth,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "indicators"
Indicator = Callable[[FloatArray, FloatArray, FloatArray], FloatArray]

PREFIX_INDICATORS: dict[str, Indicator] = {
    "sma_20": lambda c, h, lo: sma(c, 20),
    "ema_50": lambda c, h, lo: ema(c, 50),
    "wilder_14": lambda c, h, lo: wilder_smooth(c, 14),
    "rsi_14": lambda c, h, lo: rsi(c, 14),
    "macd_hist": lambda c, h, lo: macd(c, 12, 26, 9).hist,
    "atr_14": lambda c, h, lo: atr(h, lo, c, 14),
    "adx_14": lambda c, h, lo: adx(h, lo, c, 14),
    "bb_upper": lambda c, h, lo: bbands(c, 20).upper,
    "highest_20": lambda c, h, lo: highest(c, 20),
    "lowest_20": lambda c, h, lo: lowest(c, 20),
    "cross": lambda c, h, lo: cross_above(ema(c, 5), ema(c, 20)).astype(np.float64),
}


@pytest.fixture(scope="module")
def ohlc() -> tuple[FloatArray, FloatArray, FloatArray]:
    frame: pd.DataFrame = pq.read_table(FIXTURES / "talib-BTCUSDT-4h-2023.parquet").to_pandas()
    return (
        frame["close"].to_numpy(dtype=np.float64),
        frame["high"].to_numpy(dtype=np.float64),
        frame["low"].to_numpy(dtype=np.float64),
    )


@pytest.mark.parametrize("name", sorted(PREFIX_INDICATORS))
@pytest.mark.parametrize("k", [30, 61, 250, 1000])
def test_indicator_prefix_invariance(
    ohlc: tuple[FloatArray, FloatArray, FloatArray], name: str, k: int
) -> None:
    close, high, low = ohlc
    fn = PREFIX_INDICATORS[name]
    full = fn(close, high, low)[:k]
    prefix = fn(close[:k], high[:k], low[:k])
    np.testing.assert_array_equal(np.isnan(full), np.isnan(prefix))
    valid = ~np.isnan(full)
    np.testing.assert_allclose(full[valid], prefix[valid], rtol=1e-12, atol=1e-12)


def test_adx_degenerate_branches_do_not_update() -> None:
    # TR acumulado 0 tras el seed: velas planas → sin actualización, sin NaN ni división por 0.
    flat = np.full(60, 100.0)
    result = adx(flat, flat, flat, 5)
    assert np.isnan(result[:9]).all()
    np.testing.assert_array_equal(result[9:], 0.0)
    # DI⁺ + DI⁻ = 0 con rango: el high sube y el low baja lo mismo cada vela → +DM = −DM = 0.
    n = 60
    high = 100.0 + np.arange(n, dtype=np.float64)
    low = 100.0 - np.arange(n, dtype=np.float64)
    close = np.full(n, 100.0)
    result = adx(high, low, close, 5)
    assert not np.isnan(result[9:]).any()
    np.testing.assert_array_equal(result[9:], 0.0)


@settings(max_examples=30, deadline=None)
@given(
    constant=st.floats(min_value=0.5, max_value=1e5, allow_nan=False, allow_infinity=False),
    leading_nans=st.integers(min_value=0, max_value=10),
    period=st.integers(min_value=2, max_value=15),
)
def test_seeded_ewm_constant_series_with_nan_prefix(
    constant: float, leading_nans: int, period: int
) -> None:
    x = np.concatenate([np.full(leading_nans, np.nan), np.full(40, constant)])
    for fn in (ema, wilder_smooth):
        result = fn(x, period)
        first_valid = leading_nans + period - 1
        assert np.isnan(result[:first_valid]).all()
        np.testing.assert_allclose(result[first_valid:], constant, rtol=1e-12)
