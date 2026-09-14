"""`regime_bh`: régimen por días UTC completos, señales y sizing por fracción en el Engine."""

from __future__ import annotations

import math

import numpy as np
import pytest

from tests.engine.fakes import bars_from, build_engine
from tests.factories import BTC, make_candle
from tests.risk.test_market_filter import DAY0, day_candles
from tradingbot.config.models import RiskConfig
from tradingbot.domain import ExitReason, Side, Timeframe
from tradingbot.domain.errors import ConfigError
from tradingbot.strategy import OhlcvArrays
from tradingbot.strategy.registry import get_strategy_class
from tradingbot.strategy.strategies import RegimeBh

OFF = {"daily_loss_limit_pct": None, "max_drawdown_pct": None}


def arrays(closes: list[str]) -> OhlcvArrays:
    candles = [c for day, close in enumerate(closes) for c in day_candles(day, close)]
    return OhlcvArrays.from_candles(candles)


def test_registered_and_warmup_is_the_finite_window() -> None:
    assert get_strategy_class("regime_bh") is RegimeBh
    strategy = RegimeBh()
    assert strategy.warmup_candles == (200 + 2) * 6
    assert RegimeBh.from_params(sma_days=3, momentum_days=2).warmup_candles == 30
    assert set(RegimeBh.search_space()) == {"sma_days", "momentum_days", "stop_pct"}


def test_regime_uses_only_complete_days() -> None:
    strategy = RegimeBh.from_params(sma_days=3, momentum_days=2)
    # Días 0..3 suben, el 4 cae; las 6 velas del día 5 quedan incompletas (solo 4).
    candles = [
        c
        for day, close in enumerate(["100", "101", "102", "103", "90"])
        for c in day_candles(day, close)
    ]
    candles += day_candles(5, "95")[:4]
    ind = strategy.compute_indicators(OhlcvArrays.from_candles(candles))
    regime = ind["regime"]
    assert np.all(
        np.isnan(regime[:17])
    )  # nada definido hasta cerrar el día 2 (3 cierres, momentum 2)
    assert regime[17] == 1.0  # cierre del día 2: 102 > SMA(100,101,102)=101 y 102/100 > 1
    assert np.all(regime[18:24] == 1.0)  # el día 3 usa el régimen del día 2 hasta su cierre
    assert regime[23] == 1.0  # cierre del día 3: 103 > 102 y 103/101 > 1
    assert np.all(regime[24:29] == 1.0)  # las velas del día 4 siguen con el régimen del día 3
    assert regime[29] == 0.0  # cierre del día 4: 90 < SMA(101,102,103)=102 -> apagado
    assert np.all(regime[30:] == 0.0)  # el día 5 (incompleto) usa el régimen del día 4
    assert ind["daily_close"][29] == 90.0
    assert math.isnan(ind["sma"][10])


def test_bars_per_day_must_match_the_timeframe() -> None:
    strategy = RegimeBh.from_params(sma_days=3, momentum_days=2)  # bars_per_day 6 (4h)
    hourly = OhlcvArrays.from_candles(
        [make_candle(open_time=DAY0 + k * 3_600_000, timeframe=Timeframe.H1) for k in range(30)]
    )
    with pytest.raises(ConfigError, match="bars_per_day"):
        strategy.compute_indicators(hourly)


def test_engine_enters_with_fraction_size_and_exits_when_regime_turns_off() -> None:
    closes = ["100", "101", "102", "103", "104", "90", "80", "85"]
    candles = [c for day, close in enumerate(closes) for c in day_candles(day, close)]
    strategy = RegimeBh.from_params(sma_days=3, momentum_days=2)
    risk = RiskConfig(**OFF, sizing_mode="fraction", position_fraction="0.6", max_positions=1)
    engine, store, _ = build_engine(strategy, bars_from(candles), {BTC: candles}, risk=risk)
    for bar in bars_from(candles):
        engine.process_bar(bar)
    buys = [f for f in store.fills() if f.side is Side.BUY]
    sells = [f for f in store.fills() if f.side is Side.SELL]
    # Régimen definido y encendido al cierre del día 2 (vela 17) -> compra al open de la vela 18.
    assert [f.fill_ts for f in buys] == [candles[18].open_time]
    assert float(buys[0].qty * buys[0].price) == pytest.approx(6000, rel=0.01)  # 60 % de 10,000
    trades = store.trades()
    assert len(trades) == 1
    assert (
        trades[0].exit_reason is ExitReason.SIGNAL
    )  # día 5 (90) apaga el régimen -> vende al open siguiente
    assert sells[0].fill_ts == candles[36].open_time  # primera vela del día 6
    position_stop = store.orders()[0].intent.stop_price
    assert position_stop == candles[17].close * (1 - __import__("decimal").Decimal("0.20"))
