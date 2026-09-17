"""Filtro de mercado a nivel cartera (ADR-0009): cierre diario al cerrar la vela de las 20:00,
EMA sembrada con SMA (o SMA), momentum; misma definición de día que `regime_bh` (ADR-0010)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.factories import BTC, ETH, H4_MS, d, make_candle, make_position
from tests.risk.test_risk import enter, manager, view
from tradingbot.backtest.runner import market_filter_states
from tradingbot.config.models import MarketFilterConfig, RiskConfig
from tradingbot.config.settings import BotConfig
from tradingbot.domain import ExitReason, Pair
from tradingbot.domain.candle import Candle
from tradingbot.risk import MarketFilter, MarketState, ReasonCode
from tradingbot.risk.market_filter import MS_PER_DAY
from tradingbot.risk.protections import PROTECTION_CLEARED, PROTECTION_TRIGGERED, Protections
from tradingbot.strategy import OhlcvArrays
from tradingbot.strategy.strategies import RegimeBh

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


def test_undefined_filter_can_fail_closed_without_changing_legacy_default() -> None:
    strict = MarketFilter(
        MarketFilterConfig(
            enabled=True,
            average="sma",
            ema_days=3,
            momentum_days=2,
            block_when_undefined=True,
        )
    )
    assert not strict.enabled
    assert MarketFilter(small_filter()).enabled
    feed(strict, RISING[:2])
    assert not strict.enabled
    restored = MarketFilter(strict._cfg)
    restored.restore(strict.to_state())
    assert not restored.enabled
    feed(restored, RISING[2:], start_day=2)
    assert restored.enabled


def test_config_validation() -> None:
    assert MarketFilterConfig().reference_pair == BTC
    assert MarketFilterConfig(pair="eth/usdt").reference_pair == ETH
    with pytest.raises(ValidationError):
        MarketFilterConfig(pair="BTCUSDT")
    assert RiskConfig().market_filter.enabled is False


def test_daily_close_is_committed_at_the_last_candle_of_the_day() -> None:
    mf = MarketFilter(MarketFilterConfig(enabled=True, ema_days=20, momentum_days=5))
    day0 = day_candles(0, "100")
    for candle in day0[:5]:
        mf.on_candle(candle)
    assert state_of(mf) is None  # el día 0 todavía no cerró (falta la vela de las 20:00)
    assert mf.enabled
    assert mf.on_candle(day0[5]) is False  # cierra el día: EMA indefinida, sigue habilitado
    committed = state_of(mf)
    assert committed is not None
    assert committed.close == d("100")
    assert committed.ema is None
    assert mf.undefined_days == 1
    assert mf.on_candle(day_candles(1, "101", pair=ETH)[5]) is False  # otro par: ignorado
    assert state_of(mf) is committed
    # Un día sin su vela de las 20:00 no se comete (misma regla que la estrategia).
    for candle in day_candles(1, "101")[:5]:
        mf.on_candle(candle)
    assert state_of(mf) is committed


def test_ema_seeded_with_sma_then_updated_and_momentum() -> None:
    mf = MarketFilter(small_filter())
    feed(mf, RISING)  # se comprometen los días 0..3 al cerrar cada vela de las 20:00
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
    # Día 4 (90): EMA = 0.5*90 + 0.5*102 = 96 > 90 -> deshabilitado al cerrar el día 4
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
    # El cierre del día 4 se conoce al cerrar su vela de las 20:00: ese es el ts del evento.
    assert events[0].ts == day_candles(4, "90")[5].close_time
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
    feed(mf, RISING)
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


def test_filter_states_match_regime_bh_candle_by_candle() -> None:
    # El benchmark "B&H filtrado" (estados del filtro con `average: sma`) y el régimen de la
    # estrategia tienen que coincidir vela por vela: misma definición de cierre diario (ADR-0010).
    closes = ["100", "101", "102", "103", "104", "90", "80", "85", "120", "130"]
    candles = [c for day, close in enumerate(closes) for c in day_candles(day, close)]
    candles += day_candles(10, "140")[:4]  # día incompleto al final
    config = BotConfig(
        strategy={"name": "regime_bh", "pairs": ["BTC/USDT"]},
        risk={
            "market_filter": {
                "enabled": True,
                "benchmark_only": True,
                "average": "sma",
                "ema_days": 3,
                "momentum_days": 2,
            }
        },
    )
    states = market_filter_states(config, [], candles)
    regime = RegimeBh.from_params(sma_days=3, momentum_days=2).compute_indicators(
        OhlcvArrays.from_candles(candles)
    )["regime"]
    for i, (state, value) in enumerate(zip(states, regime, strict=True)):
        expected = True if value != value else bool(value)  # NaN -> el filtro queda habilitado
        assert state is expected, i
