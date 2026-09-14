"""`RollingSeries` (live) da los mismos indicadores que `PrecomputedSeries` (backtest)."""

from __future__ import annotations

import math

import pytest

from tests.factories import BTC
from tests.risk.test_market_filter import day_candles
from tradingbot.domain import Bar, DataError
from tradingbot.engine import PrecomputedSeries, RollingSeries
from tradingbot.strategy.strategies import RegimeBh


def test_rolling_matches_precomputed_and_keeps_only_the_window() -> None:
    closes = ["100", "101", "102", "103", "104", "90", "80", "85", "120", "130"]
    candles = [c for day, close in enumerate(closes) for c in day_candles(day, close)]
    strategy = RegimeBh.from_params(sma_days=3, momentum_days=2)
    window = strategy.warmup_candles + 1  # 31 velas
    warm, live = candles[:window], candles[window:]
    rolling = RollingSeries(strategy, {BTC: warm}, window=window)
    precomputed = PrecomputedSeries(strategy, {BTC: candles})
    assert rolling.pairs == (BTC,)
    for candle in live:
        bar = Bar.from_candles([candle])
        live_at = rolling.at(BTC, bar)
        full_at = precomputed.at(BTC, bar)
        assert live_at is not None
        assert full_at is not None
        assert live_at.index == window - 1
        assert len(live_at.ohlcv) == window
        for name in ("regime", "momentum", "sma"):
            a = float(live_at.indicators[name][live_at.index])
            b = float(full_at.indicators[name][full_at.index])
            assert (math.isnan(a) and math.isnan(b)) or a == pytest.approx(b), (
                name,
                candle.open_time,
            )
    assert len(rolling.history(BTC)) == window


def test_rolling_replaces_same_candle_and_rejects_out_of_order() -> None:
    candles = day_candles(0, "100") + day_candles(1, "101")
    strategy = RegimeBh.from_params(sma_days=3, momentum_days=2)
    rolling = RollingSeries(strategy, {BTC: candles[:6]}, window=12)
    assert rolling.at(BTC, Bar.from_candles([candles[6]])) is not None
    replaced = candles[6].model_copy(update={"close": candles[6].close + 1})
    at = rolling.at(BTC, Bar.from_candles([replaced]))
    assert at is not None
    assert len(rolling.history(BTC)) == 7  # misma vela: reemplaza, no duplica
    with pytest.raises(DataError, match="anterior"):
        rolling.at(BTC, Bar.from_candles([candles[3]]))
    assert rolling.at(BTC, Bar.from_candles([day_candles(2, "102")[0]])) is not None
    with pytest.raises(ValueError, match="window"):
        RollingSeries(strategy, {}, window=0)
