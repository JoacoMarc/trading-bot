from __future__ import annotations

import numpy as np
import pytest

from tradingbot.indicators import FloatArray, ema
from tradingbot.strategy import OhlcvArrays
from tradingbot.strategy.strategies import EmaTrend, RegimeBh
from tradingbot.validation import (
    assert_equivalent,
    check_no_lookahead,
    check_window_equivalence,
    signal_at,
)

SMALL = {
    "ema_fast": 5,
    "ema_slow": 12,
    "ema_regime": 30,
    "adx_period": 5,
    "atr_period": 5,
    "warmup_multiplier": 6,
}


class LeakyEmaTrend(EmaTrend):
    """Variante que mira una vela hacia adelante: debe ser detectada."""

    name = "leaky_test"

    def compute_indicators(self, ohlcv: OhlcvArrays) -> dict[str, FloatArray]:
        indicators = super().compute_indicators(ohlcv)
        shifted = np.roll(ohlcv.close, -1)  # close(t+1) en la posición t
        indicators["ema_fast"] = ema(shifted, self.params.ema_fast)
        return indicators


class ShortWarmupEmaTrend(EmaTrend):
    """Warmup insuficiente: la ventana no reproduce la serie completa."""

    name = "short_test"

    @property
    def warmup_candles(self) -> int:
        return self.longest_period + 5


def test_ema_trend_default_is_equivalent_on_real_data(btc_2023: OhlcvArrays) -> None:
    no_lookahead, window = assert_equivalent(EmaTrend(), btc_2023, samples=12, seed=1)
    assert no_lookahead.ok
    assert window.ok
    assert len(no_lookahead.samples) == 12
    assert all(t >= 1200 for t in no_lookahead.samples)
    assert max(window.max_rel_diff.values()) < 1e-4
    assert "OK" in window.summary()


def test_small_params_equivalent_on_eth(eth_2023: OhlcvArrays) -> None:
    strategy = EmaTrend.from_params(**SMALL)
    assert check_no_lookahead(strategy, eth_2023, samples=30, seed=3).ok
    assert check_window_equivalence(strategy, eth_2023, samples=30, seed=3).ok


def test_lookahead_is_detected(btc_2023: OhlcvArrays) -> None:
    leaky = LeakyEmaTrend.from_params(**SMALL)
    report = check_no_lookahead(leaky, btc_2023, samples=25, seed=0)
    assert not report.ok
    assert "fallas" in report.summary()
    assert any("señal" in f or "trailing" in f for f in report.failures)
    # la equivalencia de ventana no lo detecta: ambas series miran el futuro por igual
    with pytest.raises(AssertionError, match="no pasa la equivalencia"):
        assert_equivalent(leaky, btc_2023, samples=25)


def test_short_warmup_is_detected(btc_2023: OhlcvArrays) -> None:
    short = ShortWarmupEmaTrend()
    report = check_window_equivalence(short, btc_2023, samples=10, seed=0)
    assert not report.ok
    assert any("ema_regime" in f for f in report.failures)


def test_signal_at_and_sampling_errors(btc_2023: OhlcvArrays) -> None:
    strategy = EmaTrend.from_params(**SMALL)
    signal, trailing = signal_at(strategy, btc_2023, index=500)
    assert signal.open_time == int(btc_2023.open_time[500])
    assert trailing is None
    with pytest.raises(ValueError, match="warmup"):
        check_no_lookahead(EmaTrend(), btc_2023.slice(0, 100))


def test_regime_bh_is_equivalent_on_real_data(btc_2023: OhlcvArrays) -> None:
    # SMA y retorno tienen memoria finita: la ventana de warmup reproduce la serie exacta.
    strategy = RegimeBh.from_params(sma_days=40, momentum_days=10)
    assert strategy.warmup_candles == (40 + 2) * 6
    no_lookahead, window = assert_equivalent(strategy, btc_2023, samples=8, seed=2)
    assert no_lookahead.ok
    assert window.ok
