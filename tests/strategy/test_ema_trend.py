from __future__ import annotations

from collections import Counter
from decimal import Decimal

import numpy as np
import pytest
from pydantic import ValidationError

from tests.factories import BTC, T0, d, make_candle
from tradingbot.domain import (
    Candle,
    ExitReason,
    Position,
    Side,
    SignalAction,
    Timeframe,
    make_client_order_id,
)
from tradingbot.strategy import OhlcvArrays, StrategyContext
from tradingbot.strategy.strategies import EmaTrend, EmaTrendParams

SMALL = {
    "ema_fast": 3,
    "ema_slow": 6,
    "ema_regime": 12,
    "adx_period": 3,
    "adx_threshold": 0.0,
    "atr_period": 3,
    "warmup_multiplier": 5,
}


def v_shaped_series(down: int = 40, up: int = 80, start: float = 200.0) -> list[Candle]:
    """Baja lineal y luego suba lineal: fuerza un cruce alcista claro tras el warmup."""
    prices = np.concatenate(
        [np.linspace(start, start - down, down), np.linspace(start - down, start + up, up)]
    )
    candles = []
    for i, price in enumerate(prices):
        p = round(float(price), 2)
        candles.append(
            make_candle(
                pair=BTC,
                open_time=T0 + i * Timeframe.H4.ms,
                open=str(p),
                high=str(round(p + 1.0, 2)),
                low=str(round(p - 1.0, 2)),
                close=str(p),
                volume="10",
            )
        )
    return candles


def run(
    strategy: EmaTrend, ohlcv: OhlcvArrays, position: Position | None = None
) -> list[tuple[int, str]]:
    indicators = strategy.compute_indicators(ohlcv)
    out = []
    for i in range(len(ohlcv)):
        ctx = StrategyContext(
            ohlcv=ohlcv,
            indicators=indicators,
            index=i,
            position=position,
            equity=Decimal(10_000),
            cash=Decimal(10_000),
        )
        out.append((i, strategy.on_candle(ctx).action.value))
    return out


def test_params_validation() -> None:
    params = EmaTrendParams()
    assert (params.ema_fast, params.ema_slow, params.ema_regime) == (20, 50, 200)
    assert params.entry_mode == "cross"
    with pytest.raises(ValidationError, match="ema_fast < ema_slow < ema_regime"):
        EmaTrendParams(ema_fast=50, ema_slow=20)
    with pytest.raises(ValidationError, match="3 decimales"):
        EmaTrendParams(stop_atr_mult=2.0001)
    with pytest.raises(ValidationError):
        EmaTrendParams(
            entry_mode="always"
        )  # pyright/mypy no lo detectan: Literal validado en runtime
    with pytest.raises(ValidationError):
        EmaTrendParams(unknown=1)  # type: ignore[call-arg]


def test_longest_period_and_warmup() -> None:
    strategy = EmaTrend.from_params(**SMALL)
    assert strategy.longest_period == 12
    assert strategy.warmup_candles == 60
    assert EmaTrend().warmup_candles == 1200


def test_holds_during_warmup_and_enters_after_bullish_cross() -> None:
    strategy = EmaTrend.from_params(**SMALL)
    ohlcv = OhlcvArrays.from_candles(v_shaped_series())
    actions = run(strategy, ohlcv)
    assert all(a == "hold" for _, a in actions[:12])  # indicadores en NaN
    enters = [i for i, a in actions if a == "enter_long"]
    assert len(enters) == 1, actions
    entry = enters[0]
    assert 40 < entry < 80  # después del mínimo, cuando la rápida cruza la lenta y close > régimen
    indicators = strategy.compute_indicators(ohlcv)
    ctx = StrategyContext(
        ohlcv=ohlcv, indicators=indicators, index=entry, equity=Decimal(1), cash=Decimal(1)
    )
    signal = strategy.on_candle(ctx)
    assert signal.action is SignalAction.ENTER_LONG
    assert signal.stop_price is not None
    assert signal.stop_price < d(str(ctx.close))
    assert signal.strength is not None
    assert signal.strength > 0
    assert "cross" in signal.note
    assert all(a == "hold" for i, a in actions if i > entry)  # sin posición, un solo cruce


def test_exit_signal_on_bearish_cross_with_open_position() -> None:
    strategy = EmaTrend.from_params(**SMALL)
    # suba y luego baja: la rápida cruza bajo la lenta en la caída
    candles = v_shaped_series(down=0, up=60) + [
        c.model_copy(update={"open_time": T0 + (60 + k) * Timeframe.H4.ms})
        for k, c in enumerate(reversed(v_shaped_series(down=0, up=60)))
    ]
    ohlcv = OhlcvArrays.from_candles(candles)
    position = Position(
        pair=BTC,
        strategy="ema_trend",
        qty=Decimal("1"),
        entry_price=d("210"),
        entry_time=T0,
        stop_price=d("200"),
        highest_close_since_entry=d("260"),
        client_order_id=make_client_order_id("ema_trend", BTC, T0, Side.BUY),
    )
    actions = run(strategy, ohlcv, position=position)
    exits = [i for i, a in actions if a == "exit_long"]
    assert len(exits) == 1
    assert exits[0] > 60
    indicators = strategy.compute_indicators(ohlcv)
    ctx = StrategyContext(ohlcv=ohlcv, indicators=indicators, index=exits[0], position=position)
    signal = strategy.on_candle(ctx)
    assert signal.exit_reason is ExitReason.SIGNAL
    assert signal.stop_price is None
    # con posición abierta nunca hay ENTER, aunque haya cruce alcista
    assert not any(a == "enter_long" for _, a in actions)


def test_trailing_stop_is_chandelier_below_highest_close() -> None:
    strategy = EmaTrend.from_params(**SMALL)
    ohlcv = OhlcvArrays.from_candles(v_shaped_series())
    indicators = strategy.compute_indicators(ohlcv)
    position = Position(
        pair=BTC,
        strategy="ema_trend",
        qty=Decimal("1"),
        entry_price=d("170"),
        entry_time=T0,
        stop_price=d("160"),
        highest_close_since_entry=d("250"),
        client_order_id=make_client_order_id("ema_trend", BTC, T0, Side.BUY),
    )
    ctx = StrategyContext(ohlcv=ohlcv, indicators=indicators, index=100, position=position)
    stop = strategy.trailing_stop(ctx)
    assert stop is not None
    atr_value = ctx.value("atr")
    assert float(stop) == pytest.approx(250 - 3.0 * atr_value, abs=1e-6)
    assert (
        strategy.trailing_stop(StrategyContext(ohlcv=ohlcv, indicators=indicators, index=100))
        is None
    )
    assert (
        strategy.trailing_stop(
            StrategyContext(ohlcv=ohlcv, indicators=indicators, index=0, position=position)
        )
        is None
    )


def test_state_mode_reenters_after_cooldown() -> None:
    strategy = EmaTrend.from_params(**SMALL, entry_mode="state", cooldown_candles=2)
    ohlcv = OhlcvArrays.from_candles(v_shaped_series())
    indicators = strategy.compute_indicators(ohlcv)
    index = 100  # tendencia alcista establecida

    def action(bars_since_exit: int | None) -> SignalAction:
        ctx = StrategyContext(
            ohlcv=ohlcv, indicators=indicators, index=index, bars_since_exit=bars_since_exit
        )
        return strategy.on_candle(ctx).action

    assert action(None) is SignalAction.ENTER_LONG
    assert action(1) is SignalAction.HOLD
    assert action(2) is SignalAction.ENTER_LONG
    cross_only = EmaTrend.from_params(**SMALL)
    ctx = StrategyContext(ohlcv=ohlcv, indicators=indicators, index=index)
    assert cross_only.on_candle(ctx).action is SignalAction.HOLD


def _hand_made_context(
    *, close: float, regime: float, adx_value: float, crossed: bool = True
) -> StrategyContext:
    """Contexto de 2 velas con indicadores construidos a mano para probar cada filtro aislado."""
    candles = [
        make_candle(
            open_time=T0, open=str(close), high=str(close + 1), low=str(close - 1), close=str(close)
        ),
        make_candle(
            open_time=T0 + Timeframe.H4.ms,
            open=str(close),
            high=str(close + 1),
            low=str(close - 1),
            close=str(close),
        ),
    ]
    prev_fast = close - 2.0 if crossed else close + 2.0
    indicators = {
        "ema_fast": np.array([prev_fast, close + 1.0]),
        "ema_slow": np.array([close, close]),
        "ema_regime": np.array([regime, regime]),
        "adx": np.array([adx_value, adx_value]),
        "atr": np.array([1.0, 1.0]),
    }
    return StrategyContext(ohlcv=OhlcvArrays.from_candles(candles), indicators=indicators, index=1)


def test_regime_and_adx_filters_block_entries() -> None:
    strategy = EmaTrend.from_params(**{**SMALL, "adx_threshold": 20.0})
    ok = strategy.on_candle(_hand_made_context(close=100.0, regime=90.0, adx_value=30.0))
    assert ok.action is SignalAction.ENTER_LONG
    assert ok.stop_price == d("98")  # close − 2 × ATR(1.0)

    bearish = strategy.on_candle(_hand_made_context(close=100.0, regime=110.0, adx_value=30.0))
    assert bearish.action is SignalAction.HOLD
    assert "régimen" in bearish.note

    flat = strategy.on_candle(_hand_made_context(close=100.0, regime=90.0, adx_value=10.0))
    assert flat.action is SignalAction.HOLD
    assert "adx" in flat.note

    no_cross = strategy.on_candle(
        _hand_made_context(close=100.0, regime=90.0, adx_value=30.0, crossed=False)
    )
    assert no_cross.action is SignalAction.HOLD


def test_default_params_on_real_btc_2023(btc_2023: OhlcvArrays) -> None:
    strategy = EmaTrend()
    indicators = strategy.compute_indicators(btc_2023)
    counts: Counter[str] = Counter()
    for i in range(strategy.warmup_candles, len(btc_2023)):
        ctx = StrategyContext(
            ohlcv=btc_2023,
            indicators=indicators,
            index=i,
            equity=Decimal(10_000),
            cash=Decimal(10_000),
        )
        signal = strategy.on_candle(ctx)
        counts[signal.action.value] += 1
        if signal.action is SignalAction.ENTER_LONG:
            assert signal.stop_price is not None
            assert signal.stop_price < d(str(ctx.close))
            assert signal.strength is not None
            assert signal.strength > strategy.params.adx_threshold
    assert counts["enter_long"] >= 2  # 2023 fue alcista: hay cruces con régimen a favor
    assert counts["exit_long"] == 0  # sin posición no hay salidas
