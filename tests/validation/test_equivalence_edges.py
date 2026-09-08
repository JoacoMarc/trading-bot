"""Ramas de la equivalencia: NaN en una sola serie y decisiones dependientes del índice."""

from __future__ import annotations

from decimal import Decimal

from tradingbot.domain import Signal, SignalAction
from tradingbot.strategy import OhlcvArrays, StrategyContext
from tradingbot.strategy.strategies import EmaTrend
from tradingbot.validation import check_window_equivalence

SMALL = {
    "ema_fast": 5,
    "ema_slow": 12,
    "ema_regime": 30,
    "adx_period": 5,
    "atr_period": 5,
    "warmup_multiplier": 6,
}


class TooShortWarmupEmaTrend(EmaTrend):
    """Warmup menor que el período más largo: la ventana ni siquiera tiene EMA200 válida."""

    name = "tooshort_tst"

    @property
    def warmup_candles(self) -> int:
        return self.longest_period - 5


class IndexLeakEmaTrend(EmaTrend):
    """Decide según la posición absoluta en la serie: distinto en backtest y en live."""

    name = "indexleak_ts"

    def on_candle(self, ctx: StrategyContext) -> Signal:
        if ctx.position is None and ctx.index > self.warmup_candles:
            return Signal(
                action=SignalAction.ENTER_LONG,
                pair=ctx.pair,
                open_time=ctx.open_time,
                stop_price=ctx.candle.close - Decimal("1"),
            )
        return Signal.hold(ctx.pair, ctx.open_time)


def test_nan_only_in_window_is_reported(btc_2023: OhlcvArrays) -> None:
    report = check_window_equivalence(TooShortWarmupEmaTrend(), btc_2023, samples=5, seed=0)
    assert not report.ok
    assert any("NaN solo en una" in f for f in report.failures)


def test_signal_mismatch_between_full_series_and_window(btc_2023: OhlcvArrays) -> None:
    strategy = IndexLeakEmaTrend.from_params(**SMALL)
    report = check_window_equivalence(strategy, btc_2023, samples=20, seed=0)
    assert not report.ok
    assert report.signal_comparisons == 40
    assert report.signal_mismatches > 0
    assert report.signal_match_rate < 1.0
    assert "señales iguales" in report.summary()
    # Con un umbral permisivo las señales distintas no cuentan como falla, pero quedan medidas.
    lenient = check_window_equivalence(
        strategy, btc_2023, samples=20, seed=0, max_signal_mismatch_rate=1.0
    )
    assert lenient.ok
    assert lenient.signal_mismatches == report.signal_mismatches
