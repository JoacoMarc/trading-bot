"""Indicadores propios vs fixtures TA-Lib y propiedades sobre series sintéticas."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tradingbot.indicators import (
    adx,
    atr,
    bbands,
    cross_above,
    cross_below,
    ema,
    highest,
    lowest,
    macd,
    rsi,
    sma,
    true_range,
    wilder_smooth,
)
from tradingbot.indicators.core import _seeded_ewm

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "indicators"
SYMBOLS = ("BTCUSDT", "ETHUSDT")


@pytest.fixture(scope="module", params=SYMBOLS)
def talib_frame(request: pytest.FixtureRequest) -> pd.DataFrame:
    frame: pd.DataFrame = pq.read_table(
        FIXTURES / f"talib-{request.param}-4h-2023.parquet"
    ).to_pandas()
    return frame


def _compare(mine: np.ndarray, ref: np.ndarray, rtol: float = 1e-9) -> None:
    """Mismo patrón de NaN (misma semilla) y valores iguales dentro de `rtol`."""
    np.testing.assert_array_equal(np.isnan(mine), np.isnan(ref))
    valid = ~np.isnan(ref)
    np.testing.assert_allclose(mine[valid], ref[valid], rtol=rtol, atol=1e-9)


def test_fixture_metadata_is_from_talib() -> None:
    meta = json.loads((FIXTURES / "talib-BTCUSDT-4h-2023.json").read_text(encoding="utf-8"))
    assert meta["talib_version"].startswith("0.")
    assert meta["rows"] == 2190
    assert meta["params"]["adx_14"] == {"timeperiod": 14}


def test_moving_averages_match_talib(talib_frame: pd.DataFrame) -> None:
    close = talib_frame["close"].to_numpy()
    _compare(sma(close, 20), talib_frame["sma_20"].to_numpy())
    for period in (20, 50, 200):
        _compare(ema(close, period), talib_frame[f"ema_{period}"].to_numpy())


def test_rsi_matches_talib(talib_frame: pd.DataFrame) -> None:
    _compare(rsi(talib_frame["close"].to_numpy(), 14), talib_frame["rsi_14"].to_numpy())


def test_macd_matches_talib(talib_frame: pd.DataFrame) -> None:
    result = macd(talib_frame["close"].to_numpy(), 12, 26, 9)
    _compare(result.macd, talib_frame["macd_12_26_9"].to_numpy())
    _compare(result.signal, talib_frame["macd_signal_12_26_9"].to_numpy())
    _compare(result.hist, talib_frame["macd_hist_12_26_9"].to_numpy())


def test_atr_and_adx_match_talib(talib_frame: pd.DataFrame) -> None:
    high, low, close = (talib_frame[c].to_numpy() for c in ("high", "low", "close"))
    _compare(atr(high, low, close, 14), talib_frame["atr_14"].to_numpy())
    _compare(adx(high, low, close, 14), talib_frame["adx_14"].to_numpy())


def test_bbands_and_extremes_match_talib(talib_frame: pd.DataFrame) -> None:
    close = talib_frame["close"].to_numpy()
    bands = bbands(close, 20, 2.0, 2.0)
    _compare(bands.upper, talib_frame["bb_upper_20_2"].to_numpy())
    _compare(bands.middle, talib_frame["bb_middle_20_2"].to_numpy())
    _compare(bands.lower, talib_frame["bb_lower_20_2"].to_numpy())
    _compare(highest(close, 20), talib_frame["max_20"].to_numpy())
    _compare(lowest(close, 20), talib_frame["min_20"].to_numpy())


# ------------------------------------------------------------------ propiedades sintéticas


def test_sma_and_ema_on_simple_series() -> None:
    x = np.arange(1.0, 11.0)
    assert np.isnan(sma(x, 3)[:2]).all()
    np.testing.assert_allclose(sma(x, 3)[2:], np.arange(2.0, 10.0))
    constant = np.full(50, 7.0)
    result = ema(constant, 10)
    assert np.isnan(result[:9]).all()
    np.testing.assert_allclose(result[9:], 7.0)
    np.testing.assert_allclose(wilder_smooth(constant, 5)[4:], 7.0)


def test_ema_seed_is_sma_of_first_period_values() -> None:
    x = np.array([1.0, 2.0, 3.0, 4.0, 10.0])
    result = ema(x, 4)
    assert result[3] == pytest.approx(2.5)
    assert result[4] == pytest.approx(2.5 + (10.0 - 2.5) * (2.0 / 5.0))


def test_rsi_extremes_and_bounds() -> None:
    rising = np.arange(1.0, 31.0)
    r = rsi(rising, 14)
    assert np.isnan(r[:14]).all()
    np.testing.assert_allclose(r[14:], 100.0)
    falling = rising[::-1].copy()
    np.testing.assert_allclose(rsi(falling, 14)[14:], 0.0)
    rng = np.random.default_rng(1)
    noisy = 100 + np.cumsum(rng.normal(size=500))
    r = rsi(noisy, 14)
    assert np.nanmin(r) >= 0.0
    assert np.nanmax(r) <= 100.0


def test_true_range_and_atr() -> None:
    high = np.array([10.0, 12.0, 11.0, 15.0])
    low = np.array([9.0, 10.0, 9.0, 12.0])
    close = np.array([9.5, 11.0, 10.0, 14.0])
    tr = true_range(high, low, close)
    assert np.isnan(tr[0])
    np.testing.assert_allclose(tr[1:], [2.5, 2.0, 5.0])
    result = atr(high, low, close, 2)
    assert np.isnan(result[:2]).all()
    assert result[2] == pytest.approx(2.25)
    assert result[3] == pytest.approx(2.25 * 0.5 + 5.0 * 0.5)


def test_adx_lookback_and_range() -> None:
    rng = np.random.default_rng(2)
    close = 100 + np.cumsum(rng.normal(size=300))
    high = close + rng.uniform(0.1, 1.0, size=300)
    low = close - rng.uniform(0.1, 1.0, size=300)
    result = adx(high, low, close, 14)
    assert np.isnan(result[:27]).all()
    assert not np.isnan(result[27:]).any()
    assert np.nanmin(result) >= 0.0
    assert np.nanmax(result) <= 100.0


def test_bbands_symmetry() -> None:
    rng = np.random.default_rng(3)
    x = 50 + rng.normal(size=200)
    bands = bbands(x, 20, 2.0, 2.0)
    valid = ~np.isnan(bands.middle)
    np.testing.assert_allclose(
        bands.upper[valid] - bands.middle[valid], bands.middle[valid] - bands.lower[valid]
    )
    assert (bands.upper[valid] >= bands.lower[valid]).all()


def test_cross_detection_including_nan_and_scalars() -> None:
    a = np.array([np.nan, 1.0, 2.0, 3.0, 2.0, 1.0, 3.0])
    b = np.array([np.nan, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0])
    np.testing.assert_array_equal(cross_above(a, b), [0, 0, 0, 1, 0, 0, 1])
    np.testing.assert_array_equal(cross_below(a, b), [0, 0, 0, 0, 0, 1, 0])
    np.testing.assert_array_equal(cross_above(a, 2.0), [0, 0, 0, 1, 0, 0, 1])
    assert not cross_above(np.array([1.0]), 0.0).any()


def test_highest_lowest() -> None:
    x = np.array([3.0, 1.0, 4.0, 1.0, 5.0])
    np.testing.assert_array_equal(highest(x, 2)[1:], [3.0, 4.0, 4.0, 5.0])
    np.testing.assert_array_equal(lowest(x, 2)[1:], [1.0, 1.0, 1.0, 1.0])


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="entero"):
        sma(np.ones(5), 0)
    with pytest.raises(ValueError, match="entero"):
        ema(np.ones(5), True)  # bool no es un período válido aunque sea subclase de int
    with pytest.raises(ValueError, match="1-D"):
        sma(np.ones((2, 2)), 2)
    with pytest.raises(ValueError, match="misma longitud"):
        atr(np.ones(5), np.ones(4), np.ones(5), 2)
    with pytest.raises(ValueError, match="menor que slow"):
        macd(np.ones(50), 26, 12, 9)
    with pytest.raises(ValueError, match="NaN intercalados"):
        _seeded_ewm(np.array([1.0, 2.0, np.nan, 4.0, 5.0]), 2, 0.5)
    with pytest.raises(ValueError, match="escalar o 1-D"):
        cross_above(np.ones(3), np.ones((3, 1)))


def test_short_series_are_all_nan() -> None:
    assert np.isnan(ema(np.ones(3), 5)).all()
    assert np.isnan(rsi(np.ones(5), 14)).all()
    assert np.isnan(adx(np.ones(10), np.ones(10), np.ones(10), 14)).all()
    assert np.isnan(true_range(np.ones(1), np.ones(1), np.ones(1))).all()
    assert np.isnan(_seeded_ewm(np.full(5, np.nan), 2, 0.5)).all()


@settings(max_examples=50, deadline=None)
@given(
    values=st.lists(
        st.floats(min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False),
        min_size=30,
        max_size=200,
    ),
    period=st.integers(min_value=2, max_value=20),
)
def test_averages_stay_within_window_bounds(values: list[float], period: int) -> None:
    x = np.asarray(values)
    for series in (sma(x, period), ema(x, period)):
        for i in range(period - 1, x.size):
            prefix = x[: i + 1]  # combinación convexa de valores pasados: nunca sale del rango
            assert series[i] <= prefix.max() + 1e-6
            assert series[i] >= prefix.min() - 1e-6
            assert not np.isnan(series[i])
