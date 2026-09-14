"""Recuperación tras reinicio (ADR-0011): estado del motor y protecciones, Bars de reposición."""

from __future__ import annotations

from pathlib import Path

from tests.engine.fakes import (
    ScriptedStrategy,
    bars_from,
    build_engine,
    candles_from_prices,
)
from tests.factories import BTC, T0, d
from tests.risk.test_market_filter import RISING, day_candles
from tradingbot.config.models import MarketFilterConfig, RiskConfig
from tradingbot.domain import Bar, ExitReason, Side, Trade
from tradingbot.engine import EngineState
from tradingbot.persistence import SqliteStore
from tradingbot.risk import ReasonCode
from tradingbot.risk.protections import Protections

OFF = {"daily_loss_limit_pct": None, "max_drawdown_pct": None}


def losing_stop_trade() -> Trade:
    return Trade(
        pair=BTC,
        strategy="scripted_tst",
        qty=d("1"),
        entry_price=d("100"),
        entry_time=T0,
        exit_price=d("90"),
        exit_time=T0 + 1,
        exit_reason=ExitReason.STOP,
        fees_quote=d("0.19"),
        entry_client_order_id="tb-scripted-BTCUSDT-1700000000-B",
        exit_client_order_id="tb-scripted-BTCUSDT-1700014400-X",
    )


def test_protections_state_round_trip_keeps_halts_cooldowns_and_filter() -> None:
    cfg = RiskConfig(
        max_drawdown_pct=d("0.10"),
        cooldown_candles_after_stop=5,
        market_filter=MarketFilterConfig(enabled=True, average="sma", ema_days=3, momentum_days=2),
    )
    original = Protections(cfg, auto_resume=False)
    original.on_bar(10, T0)
    original.on_equity(T0, d("10000"))
    original.on_equity(T0 + 1, d("8900"))  # DD 11 % -> halt (sin reanudación automática)
    original.on_trade_closed(losing_stop_trade())
    for day, close in enumerate([*RISING, "90"]):
        for candle in day_candles(day, close):
            original.on_reference_candle(candle)
    original.pop_events()
    state = original.to_state()

    restored = Protections(cfg, auto_resume=False)
    restored.restore(state)
    assert restored.drawdown_halted
    assert restored.peak_equity == d("10000")
    block = restored.global_block()
    assert block is not None
    assert block.reason is ReasonCode.DRAWDOWN_HALT
    assert restored.pair_block(BTC) is not None  # cooldown de 5 velas desde el bar 10
    restored.on_bar(15, T0 + 2)
    assert restored.pair_block(BTC) is None
    assert restored.market_filter is not None
    assert not restored.market_filter.enabled  # el día 4 (90) apagó el filtro
    assert restored.market_filter.status() == original.market_filter.status()  # type: ignore[union-attr]
    assert restored.to_state()["market_filter"] == state["market_filter"]


def test_engine_state_survives_sqlite_and_restores_positions_and_stops(tmp_path: Path) -> None:
    # Motor A: entra en la vela 0, sube el trailing en la 2 y muere. Motor B reanuda desde la DB.
    prices = [
        ("100", "101", "99", "100"),
        ("100", "101", "99", "100"),
        ("100", "121", "99", "120"),
        ("120", "121", "119", "120"),
    ]
    candles = candles_from_prices(prices)
    bars = bars_from(candles)
    strategy = ScriptedStrategy({T0: ("enter", "90")}, trailing={bars[2].open_time: "110"})
    store = SqliteStore(tmp_path / "paper.db")
    engine_a, _, broker_a = build_engine(
        strategy, bars, {BTC: candles}, risk=RiskConfig(**OFF), store=store
    )
    for bar in bars[:3]:
        engine_a.process_bar(bar)
    position = engine_a.positions.get(BTC)
    assert position is not None
    assert position.stop_price == d("110")
    state_a = engine_a.state()
    store.save_state("engine", state_a.to_dict())
    assert state_a.last_bar_open_time == bars[2].open_time

    loaded = store.load_state("engine")
    assert loaded is not None
    restored = EngineState.from_dict(loaded, store.load_open_positions())
    assert restored.cash == engine_a.cash
    assert restored.positions == (position,)
    assert restored.marks == {BTC: d("120")}
    assert restored.bar_index == 2

    fresh_strategy = ScriptedStrategy({})
    engine_b, _, broker_b = build_engine(
        fresh_strategy,
        bars[3:],
        {BTC: candles},
        risk=RiskConfig(**OFF),
        store=store,
        restore=restored,
    )
    assert engine_b.cash == engine_a.cash
    assert engine_b.positions.get(BTC) == position
    assert engine_b.equity() == engine_a.equity()
    stop = broker_b.get_stop(BTC)
    assert stop is not None
    assert stop.stop_price == d("110")
    assert stop.exit_reason is ExitReason.TRAILING  # el stop está sobre la entrada
    assert (
        broker_a.get_stop(BTC) is not None
    )  # el broker viejo no importa: se re-publicó en el nuevo
    engine_b.process_bar(bars[3])
    assert engine_b.state().bar_index == 3
    assert engine_b.state().last_bar_open_time == bars[3].open_time


def test_replay_bars_do_not_open_entries_but_do_exit_and_evaluate_stops() -> None:
    prices = [
        ("100", "101", "99", "100"),  # 0: entra
        ("100", "101", "99", "100"),  # 1: fill; luego señal de salida (reposición) -> se ejecuta
        ("100", "101", "99", "100"),  # 2: venta al open; nueva entrada (reposición) -> rechazada
        ("100", "101", "99", "100"),  # 3: entrada en vivo -> aceptada
    ]
    candles = candles_from_prices(prices)
    live = bars_from(candles)
    t = [c.open_time for c in candles]
    strategy = ScriptedStrategy(
        {t[0]: ("enter", "90"), t[1]: ("exit", None), t[2]: ("enter", "90"), t[3]: ("enter", "90")}
    )
    replay = [Bar.from_candles(list(b.candles.values()), replay=True) for b in live[1:3]]
    engine, store, _ = build_engine(strategy, live, {BTC: candles}, risk=RiskConfig(**OFF))
    engine.process_bar(live[0])
    engine.process_bar(replay[0])  # la salida por señal sí se ejecuta en reposición
    engine.process_bar(replay[1])  # la entrada no
    engine.process_bar(live[3])
    fills = store.fills()
    assert [f.side for f in fills] == [
        Side.BUY,
        Side.SELL,
    ]  # la entrada de la vela 2 nunca se envió
    assert engine.stats.rejections[ReasonCode.REPLAY.value] == 1
    rejected = [e for e in store.events() if e.kind == "entry_rejected"]
    assert rejected[0].reason == "replay"
    assert len(engine.positions.positions) == 0
    assert (
        len(store.orders()) == 3
    )  # compra 0, venta 1 y la compra en vivo de la vela 3 (pendiente)


class ExplodingStrategy(ScriptedStrategy):
    """Explota al evaluar la vela `boom` (simula un bug a mitad de ciclo)."""

    name = "boom_tst"

    def __init__(self, boom: int) -> None:
        super().__init__({})
        self.boom = boom

    def on_candle(self, ctx):  # type: ignore[no-untyped-def]
        if ctx.open_time == self.boom:
            msg = "bug a mitad de vela"
            raise RuntimeError(msg)
        return super().on_candle(ctx)


def test_failed_bar_is_not_marked_as_processed() -> None:
    candles = candles_from_prices([("100", "101", "99", "100")] * 3)
    bars = bars_from(candles)
    engine, _, _ = build_engine(ExplodingStrategy(bars[1].open_time), bars, {BTC: candles})
    engine.process_bar(bars[0])
    assert engine.state().last_bar_open_time == bars[0].open_time
    import pytest

    with pytest.raises(RuntimeError, match="mitad de vela"):
        engine.process_bar(bars[1])
    # La vela 1 no quedó como procesada: al reiniciar se repone desde ella.
    assert engine.state().last_bar_open_time == bars[0].open_time
