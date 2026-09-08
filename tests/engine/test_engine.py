"""El loop del `Engine` sobre escenarios sintéticos con resultado conocido."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.fakes import (
    H4,
    MARKETS,
    ScriptedStrategy,
    bars_from,
    build_engine,
    candles_from_prices,
    market,
)
from tests.factories import BTC, ETH, T0, d
from tradingbot.config.models import ExecutionConfig, RiskConfig
from tradingbot.domain import ExitReason, Fill, OrderStatus, Side, Signal
from tradingbot.engine import Engine, EngineResult
from tradingbot.persistence import InMemoryStore
from tradingbot.strategy import StrategyContext

# open, high, low, close
FLAT = [("100", "101", "99", "100")] * 8


def run(engine: Engine) -> EngineResult:
    return asyncio.run(engine.run())


def sell_fill(store: InMemoryStore) -> Fill:
    return next(f for f in store.fills() if f.side is Side.SELL)


def test_signal_at_close_t_fills_at_open_t_plus_1_with_slippage_and_fee() -> None:
    prices = [("100", "101", "99", "100"), ("102", "104", "101", "103"), *FLAT[:3]]
    candles = candles_from_prices(prices)
    strategy = ScriptedStrategy({T0: ("enter", "90")})
    engine, store, broker = build_engine(strategy, bars_from(candles), {BTC: candles})
    result = run(engine)

    fills = store.fills()
    assert len(fills) == 1
    fill = fills[0]
    assert fill.fill_ts == T0 + H4  # open de t+1
    assert fill.ref_price == Decimal("102")
    assert fill.price == Decimal("102.06")  # 102 × 1.0005 = 102.051 -> tick 0.01 hacia arriba
    # riesgo 1 % de 10 000 = 100 USDT sobre distancia 10 -> 10 unidades
    assert fill.qty == Decimal("10")
    assert fill.fee_asset == "BTC"
    assert fill.fee_amount == Decimal("0.01")
    position = engine.positions.get(BTC)
    assert position is not None
    assert position.qty == Decimal("9.99")  # neta de fee en base
    assert position.entry_price == Decimal("102.06")
    assert position.stop_price == Decimal("92.06")  # re-anclado: fill − (100 − 90)
    assert engine.cash == Decimal("10000") - Decimal("1020.6")
    stop = broker.get_stop(BTC)
    assert stop is not None
    assert stop.stop_price == Decimal("92.06")
    assert stop.exit_reason is ExitReason.STOP
    assert stop.qty == Decimal("9.99")
    order = store.orders()[0]
    assert order.status is OrderStatus.FILLED
    assert result.stats.fills == 1
    assert result.final_snapshot is not None
    assert result.final_snapshot.equity == engine.cash + Decimal("9.99") * Decimal("100")
    assert len(store.snapshots()) == len(prices)


def test_exit_signal_closes_position_and_records_trade() -> None:
    prices = [
        ("100", "101", "99", "100"),
        ("102", "104", "101", "103"),
        ("103", "105", "102", "104"),
        ("110", "111", "109", "110"),
        ("110", "111", "109", "110"),
    ]
    candles = candles_from_prices(prices)
    strategy = ScriptedStrategy({T0: ("enter", "90"), T0 + 2 * H4: ("exit", None)})
    engine, store, broker = build_engine(strategy, bars_from(candles), {BTC: candles})
    run(engine)

    trades = store.trades()
    assert len(trades) == 1
    trade = trades[0]
    assert trade.exit_reason is ExitReason.SIGNAL
    assert trade.exit_time == T0 + 3 * H4  # open de t+1 tras la señal en t = 2
    assert trade.exit_price == Decimal("109.94")  # 110 × 0.9995 = 109.945 -> tick hacia abajo
    assert trade.qty == Decimal("9.99")
    sell = sell_fill(store)
    assert sell.fee_asset == "USDT"
    assert sell.fee_amount == Decimal("109.94") * Decimal("9.99") * Decimal("0.001")
    assert trade.fees_quote == Decimal("0.01") * Decimal("102.06") + sell.fee_amount
    assert trade.pnl == (Decimal("109.94") - Decimal("102.06")) * Decimal("9.99") - trade.fees_quote
    assert engine.positions.get(BTC) is None
    assert broker.get_stop(BTC) is None
    assert engine.cash == Decimal("10000") - Decimal("1020.6") + sell.net_quote_amount
    assert engine.dust == {}
    # bars_since_exit: 0 en la vela cuyo cierre sigue al fill (t = 3), 1 en la siguiente
    since = {t: b for _, t, b, _ in strategy.seen}
    assert since[T0 + 2 * H4] is None
    assert since[T0 + 3 * H4] == 0
    assert since[T0 + 4 * H4] == 1


@pytest.mark.parametrize(
    ("bar", "expected_ref", "expected_price", "expected_ts_offset"),
    [
        (("90", "93", "88", "91"), "90", "89.95", 0),  # gap: open <= stop -> fill al open
        (("95", "96", "91", "94"), "92.06", "92.01", H4 - 1),  # toque -> fill al stop, al close
    ],
)
def test_stop_executes_with_gap_or_touch(
    bar: tuple[str, str, str, str], expected_ref: str, expected_price: str, expected_ts_offset: int
) -> None:
    prices = [
        ("100", "101", "99", "100"),
        ("102", "104", "101", "103"),
        bar,
        ("95", "96", "94", "95"),
    ]
    candles = candles_from_prices(prices)
    strategy = ScriptedStrategy({T0: ("enter", "90")})
    engine, store, _ = build_engine(strategy, bars_from(candles), {BTC: candles})
    run(engine)
    trade = store.trades()[0]
    assert trade.exit_reason is ExitReason.STOP
    assert trade.exit_time == T0 + 2 * H4 + expected_ts_offset
    assert trade.exit_price == Decimal(expected_price)
    sell = sell_fill(store)
    assert sell.ref_price == Decimal(expected_ref)
    assert sell.shortfall_bps > 0
    assert engine.positions.get(BTC) is None


def test_stop_not_touched_keeps_position() -> None:
    prices = [("100", "101", "99", "100"), ("102", "104", "101", "103"), ("95", "96", "93", "94")]
    candles = candles_from_prices(prices)
    engine, store, _ = build_engine(
        ScriptedStrategy({T0: ("enter", "90")}), bars_from(candles), {BTC: candles}
    )
    run(engine)
    assert store.trades() == ()
    assert engine.positions.get(BTC) is not None


def test_trailing_only_raises_and_reports_trailing_exit() -> None:
    prices = [
        ("100", "101", "99", "100"),
        ("102", "104", "101", "103"),
        ("110", "112", "109", "111"),  # trailing propone 105
        ("111", "113", "110", "112"),  # trailing propone 100 (menor): se ignora
        ("106", "107", "103", "104"),  # open > 105 y low 103 <= 105 -> stop trailing al nivel
    ]
    candles = candles_from_prices(prices)
    strategy = ScriptedStrategy(
        {T0: ("enter", "90")}, trailing={T0 + 2 * H4: "105", T0 + 3 * H4: "100"}
    )
    engine, store, broker = build_engine(strategy, bars_from(candles), {BTC: candles})
    run(engine)
    trade = store.trades()[0]
    assert trade.exit_reason is ExitReason.TRAILING
    assert trade.exit_time == T0 + 5 * H4 - 1  # toque intra-vela: se fecha al close de t = 4
    assert trade.exit_price == Decimal("104.94")  # 105 × 0.9995 = 104.9475 -> 104.94
    assert broker.get_stop(BTC) is None
    positions_saved = [p for p in store.load_open_positions()]
    assert positions_saved == []


def test_stuck_position_when_exit_notional_below_min() -> None:
    prices = [
        ("100", "101", "99", "100"),
        ("102", "104", "101", "103"),
        ("103", "104", "102", "103"),
        *FLAT[:2],
    ]
    candles = candles_from_prices(prices)
    strategy = ScriptedStrategy({T0: ("enter", "90"), T0 + 2 * H4: ("exit", None)})
    bars = bars_from(candles)
    engine, store, broker = build_engine(strategy, bars, {BTC: candles})
    engine.process_bar(bars[0])  # señal de entrada
    engine.process_bar(bars[1])  # fill de la compra
    assert engine.positions.get(BTC) is not None
    # forzamos el STUCK subiendo el minNotional después de comprar
    engine._risk.markets = {BTC: market(BTC, min_notional="1000000"), ETH: market(ETH)}
    for bar in bars[2:]:
        engine.process_bar(bar)
    assert engine.positions.get(BTC) is not None
    assert store.trades() == ()
    events = [e for e in store.events() if e.kind == "exit_stuck"]
    assert len(events) == 1  # se reporta una sola vez
    assert events[0].reason == "min_notional"
    assert BTC in engine.stats.stuck_pairs
    assert broker.get_stop(BTC) is not None  # el stop en reposo sigue protegiendo


def test_max_positions_ranks_by_strength_and_records_rejection() -> None:
    btc = candles_from_prices(
        [("100", "101", "99", "100"), ("100", "101", "99", "100"), ("100", "101", "99", "100")], BTC
    )
    eth = candles_from_prices(
        [("10", "11", "9.5", "10"), ("10", "11", "9.5", "10"), ("10", "11", "9.5", "10")], ETH
    )

    class PerPair(ScriptedStrategy):
        def on_candle(self, ctx: StrategyContext) -> Signal:
            signal = super().on_candle(ctx)
            if ctx.pair == BTC and signal.action.value == "enter_long":
                return signal.model_copy(update={"stop_price": d("90"), "strength": 10.0})
            return signal

    strategy = PerPair({T0: ("enter", "9")}, strengths={T0: 30.0})
    engine, store, _ = build_engine(
        strategy, bars_from(btc, eth), {BTC: btc, ETH: eth}, risk=RiskConfig(max_positions=1)
    )
    run(engine)
    assert set(engine.positions.positions) == {ETH}  # mayor strength gana el único slot
    rejected = [e for e in store.events() if e.kind == "entry_rejected"]
    assert len(rejected) == 1
    assert rejected[0].pair == BTC
    assert rejected[0].reason == "max_positions"
    assert engine.stats.rejections["max_positions"] == 1


def test_pending_order_waits_when_pair_missing_from_bar() -> None:
    btc = candles_from_prices(
        [("100", "101", "99", "100"), ("100", "101", "99", "100"), ("120", "121", "119", "120")],
        BTC,
    )
    eth = candles_from_prices([("10", "11", "9", "10")] * 3, ETH)
    del btc[1]  # hueco de BTC en la segunda vela
    strategy = ScriptedStrategy({T0: ("enter", "90")})
    engine, store, _ = build_engine(strategy, bars_from(btc, eth), {BTC: btc, ETH: eth})
    run(engine)
    fill = store.fills()[0]
    assert fill.fill_ts == T0 + 2 * H4  # se llenó en la primera vela disponible del par
    assert fill.ref_price == Decimal("120")
    assert len(store.snapshots()) == 3


def test_bnb_fee_is_charged_in_quote() -> None:

    prices = [("100", "101", "99", "100"), ("100", "101", "99", "100"), ("100", "101", "99", "100")]
    candles = candles_from_prices(prices)
    execution = ExecutionConfig(pay_with_bnb=True, slippage_bps=Decimal("0"))
    engine, store, _ = build_engine(
        ScriptedStrategy({T0: ("enter", "90")}),
        bars_from(candles),
        {BTC: candles},
        execution=execution,
    )
    run(engine)
    fill = store.fills()[0]
    assert fill.fee_asset == "USDT"
    assert fill.price == Decimal("100")
    assert fill.qty == Decimal("10")
    assert fill.fee_amount == Decimal("1000") * Decimal("0.00075")
    position = engine.positions.get(BTC)
    assert position is not None
    assert position.qty == Decimal("10")  # la fee no descuenta base
    assert engine.cash == Decimal("10000") - Decimal("1000") - fill.fee_amount


def test_engine_rejects_non_positive_cash() -> None:
    candles = candles_from_prices(FLAT[:2])
    with pytest.raises(ValueError, match="initial_cash"):
        build_engine(ScriptedStrategy(), bars_from(candles), {BTC: candles}, cash="0")


@settings(max_examples=25, deadline=None)
@given(
    moves=st.lists(st.integers(min_value=-8, max_value=8), min_size=6, max_size=40),
    actions=st.lists(st.sampled_from(["enter", "exit", "hold", "hold"]), min_size=6, max_size=40),
)
def test_portfolio_invariants_on_random_paths(moves: list[int], actions: list[str]) -> None:
    n = min(len(moves), len(actions))
    price = 100.0
    prices = []
    for m in moves[:n]:
        open_ = price
        close = max(5.0, price + m)
        high = max(open_, close) + 1
        low = min(open_, close) - 1
        prices.append((f"{open_:.2f}", f"{high:.2f}", f"{low:.2f}", f"{close:.2f}"))
        price = close
    candles = candles_from_prices(prices)
    script: dict[int, tuple[str, str | None]] = {}
    for i, action in enumerate(actions[:n]):
        if action == "enter":
            script[T0 + i * H4] = ("enter", f"{float(prices[i][3]) * 0.9:.2f}")
        elif action == "exit":
            script[T0 + i * H4] = ("exit", None)
    engine, store, _ = build_engine(ScriptedStrategy(script), bars_from(candles), {BTC: candles})
    run(engine)

    assert engine.cash >= 0
    assert len(store.snapshots()) == n
    for snapshot in store.snapshots():
        assert snapshot.equity >= 0
        assert len(snapshot.positions) <= 1
        for position in snapshot.positions:
            assert position.qty > 0
    for trade in store.trades():
        assert trade.qty > 0
        assert trade.exit_time > trade.entry_time
    sells = [f for f in store.fills() if f.side is Side.SELL]
    buys = [f for f in store.fills() if f.side is Side.BUY]
    assert len(sells) <= len(buys)
    assert len(store.trades()) == len(sells)
    total_dust = sum(engine.dust.values(), Decimal(0))
    assert total_dust >= 0
    assert set(MARKETS) >= set(engine.positions.positions)
