"""Filtro de mercado a nivel cartera (ADR-0009): cierre diario, EMA sembrada con SMA, momentum."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.factories import BTC, ETH, H4_MS, d, make_candle, make_position
from tests.risk.test_risk import enter, manager, view
from tradingbot.config.models import MarketFilterConfig, RiskConfig
from tradingbot.domain import ExitReason, Pair
from tradingbot.domain.candle import Candle
from tradingbot.risk import MarketFilter, MarketState, ReasonCode
from tradingbot.risk.market_filter import MS_PER_DAY
from tradingbot.risk.protections import PROTECTION_CLEARED, PROTECTION_TRIGGERED, Protections

DAY0 = 1_700_006_400_000 - 1_700_006_400_000 % MS_PER_DAY  # medianoche UTC
RISING = ["100", "101", "102", "103"]  # EMA(3) definida y momentum(2) > 0 al cerrar el día 3


def day_candles(day: int, close: str, pair: Pair = BTC) -> list[Candle]:
    """Seis velas de 4h de un día UTC; la última (20:00) fija el cierre diario."""
    start = DAY0 + day * MS_PER_DAY
    return [
        make_candle(
            pair=pair,
            open_time=start + k * H4_MS,
            open=close,
            high=str(float(close) + 1),
            low=str(float(close) - 1),
            close=close,
        )
        for k in range(6)
    ]


def state_of(mf: MarketFilter) -> MarketState | None:
    return mf.state  # vía función: mypy no estrecha la propiedad entre llamadas


def feed(mf: MarketFilter, closes: list[str], start_day: int = 0) -> None:
    for day, close in enumerate(closes, start=start_day):
        for candle in day_candles(day, close):
            mf.on_candle(candle)


def small_filter() -> MarketFilterConfig:
    return MarketFilterConfig(enabled=True, ema_days=3, momentum_days=2)


def test_config_validation() -> None:
    assert MarketFilterConfig().reference_pair == BTC
    assert MarketFilterConfig(pair="eth/usdt").reference_pair == ETH
    with pytest.raises(ValidationError):
        MarketFilterConfig(pair="BTCUSDT")
    assert RiskConfig().market_filter.enabled is False


def test_daily_close_is_committed_when_the_next_day_starts() -> None:
    mf = MarketFilter(MarketFilterConfig(enabled=True, ema_days=20, momentum_days=5))
    for candle in day_candles(0, "100"):
        mf.on_candle(candle)
    assert state_of(mf) is None  # el día 0 todavía no cerró
    assert mf.enabled
    first_of_day_1 = day_candles(1, "101")[0]
    assert mf.on_candle(first_of_day_1) is False  # EMA indefinida: sigue habilitado, sin cambio
    committed = state_of(mf)
    assert committed is not None
    assert committed.close == d("100")
    assert committed.ema is None
    assert mf.undefined_days == 1
    assert mf.on_candle(day_candles(1, "101", pair=ETH)[1]) is False  # otro par: ignorado


def test_ema_seeded_with_sma_then_updated_and_momentum() -> None:
    mf = MarketFilter(small_filter())
    feed(mf, [*RISING, "140"])  # se comprometen los días 0..3; el 4 sigue abierto
    state = state_of(mf)
    assert state is not None
    assert state.close == d("103")
    # SMA(100,101,102) = 101 al tercer día; luego EMA(alpha=0.5): 0.5*103 + 0.5*101 = 102
    assert state.ema == pytest.approx(102.0)
    assert state.momentum == pytest.approx(103 / 101 - 1)
    assert state.enabled  # 103 > 102 y momentum > 0
    assert mf.undefined_days == 2  # días 0 y 1 sin EMA ni momentum


def test_filter_disables_on_crash_and_reenables_on_recovery() -> None:
    mf = MarketFilter(small_filter())
    feed(mf, [*RISING, "90", "80", "85"])
    # Día 4 (90): EMA = 0.5*90 + 0.5*102 = 96 > 90 -> deshabilitado al abrir el día 5
    assert not mf.enabled
    status = mf.status()
    assert status["market_filter"] == "deshabilitado"
    assert "momentum" in status["detail"]
    feed(mf, ["120", "130", "140", "150"], start_day=7)
    assert mf.enabled  # vuelve a habilitar con precio sobre la EMA y momentum positivo


def test_flat_prices_disable_the_filter() -> None:
    # Momentum exactamente cero no es tendencia: el filtro exige > 0.
    mf = MarketFilter(small_filter())
    feed(mf, ["100"] * 5)
    assert not mf.enabled


def test_protections_block_entries_but_never_exits_when_market_is_off() -> None:
    risk = RiskConfig(
        daily_loss_limit_pct=None, max_drawdown_pct=None, market_filter=small_filter()
    )
    m = manager(risk)
    p: Protections = m.protections
    assert p.market_filter is not None
    for day, close in enumerate([*RISING, "90", "80", "85"]):
        for candle in day_candles(day, close):
            p.on_reference_candle(candle)
    block = p.global_block()
    assert block is not None
    assert block.reason is ReasonCode.MARKET_FILTER
    assert "BTC/USDT" in block.detail
    events = p.pop_events()
    assert [e.reason for e in events] == [ReasonCode.MARKET_FILTER]
    assert events[0].kind == PROTECTION_TRIGGERED
    # El cierre del día 4 se conoce con la primera vela del día 5: ese es el ts del evento.
    assert events[0].ts == day_candles(5, "80")[0].close_time
    decision = m.evaluate_entries([enter(BTC), enter(ETH, stop="9")], view(), events[0].ts)
    assert decision.intents == ()
    assert {r.reason for r in decision.rejections} == {ReasonCode.MARKET_FILTER}
    exit_decision = m.exit_intent(
        make_position(pair=BTC, qty="1"), ExitReason.SIGNAL, d("80"), 0, 0
    )
    assert exit_decision.intent is not None  # las salidas no dependen del filtro
    for day, close in enumerate(["120", "130", "140", "150"], start=7):
        for candle in day_candles(day, close):
            p.on_reference_candle(candle)
    assert p.global_block() is None
    assert [e.kind for e in p.pop_events()] == [PROTECTION_CLEARED]
    assert p.status()["market_filter"] == "habilitado"


def test_disabled_filter_is_not_created() -> None:
    assert manager(RiskConfig()).protections.market_filter is None
    assert manager(RiskConfig()).protections.status()["market_filter"] == "off"


def test_sma_average_matches_rolling_mean() -> None:
    mf = MarketFilter(MarketFilterConfig(enabled=True, average="sma", ema_days=3, momentum_days=2))
    feed(mf, [*RISING, "140"])
    state = state_of(mf)
    assert state is not None
    assert state.ema == pytest.approx((101 + 102 + 103) / 3)
    assert state.enabled


def test_benchmark_only_filter_does_not_block_entries() -> None:
    risk = RiskConfig(
        market_filter=MarketFilterConfig(
            enabled=True, benchmark_only=True, ema_days=3, momentum_days=2
        )
    )
    assert manager(risk).protections.market_filter is None
