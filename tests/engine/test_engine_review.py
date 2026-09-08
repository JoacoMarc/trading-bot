"""Casos que surgieron de la revisión de la Fase 4: cash insuficiente, slots, trailing sobre el
mercado, stops que el exchange rechazaría, salidas trabadas y reintentos."""

from __future__ import annotations

import asyncio
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.fakes import (
    H4,
    MARKETS,
    MultiScriptedStrategy,
    ScriptedStrategy,
    bars_from,
    build_engine,
    candles_from_prices,
    market,
)
from tests.factories import BTC, ETH, T0, d
from tradingbot.config.models import ExecutionConfig, RiskConfig
from tradingbot.domain import ExitReason, OrderStatus, Pair, Side
from tradingbot.engine import Engine, EngineResult

LTC = Pair(base="LTC", quote="USDT")
FULL_ALLOCATION = RiskConfig(
    risk_per_trade=d("0.05"), max_position_pct=d("1"), max_exposure_pct=d("1")
)


def run(engine: Engine) -> EngineResult:
    return asyncio.run(engine.run())


def test_buy_without_enough_cash_is_rejected_not_filled() -> None:
    # stop muy cercano + 100 % del cash: el sizing agota el cash al close 100 y el open de t+1
    # abre 0.1 % arriba -> el costo real supera el cash -> rechazo, como -2010 en Binance.
    prices = [
        ("100", "101", "99", "100"),
        ("100.10", "101", "99", "100"),
        ("100", "101", "99", "100"),
    ]
    candles = candles_from_prices(prices)
    engine, store, _ = build_engine(
        ScriptedStrategy({T0: ("enter", "99.9")}),
        bars_from(candles),
        {BTC: candles},
        risk=FULL_ALLOCATION,
    )
    run(engine)
    assert engine.cash == Decimal("10000")
    assert engine.positions.get(BTC) is None
    assert store.fills() == ()
    order = store.orders()[0]
    assert order.status is OrderStatus.REJECTED
    events = [e for e in store.events() if e.kind == "entry_rejected"]
    assert len(events) == 1
    assert events[0].reason == "insufficient_funds"
    assert engine.stats.rejections["insufficient_funds"] == 1
    assert all(s.cash >= 0 for s in store.snapshots())


@settings(max_examples=25, deadline=None)
@given(
    gaps=st.lists(st.integers(min_value=-300, max_value=300), min_size=4, max_size=25),
    position_pct=st.sampled_from(["0.25", "0.5", "1"]),
)
def test_cash_never_negative_with_full_allocation(gaps: list[int], position_pct: str) -> None:
    prices = []
    close = 100.0
    for gap_bps in gaps:
        open_ = max(1.0, close * (1 + gap_bps / 10_000))
        close = max(1.0, open_ * (1 + (gap_bps % 7 - 3) / 100))
        high = max(open_, close) + 0.5
        low = min(open_, close) - 0.5
        prices.append((f"{open_:.2f}", f"{high:.2f}", f"{low:.2f}", f"{close:.2f}"))
    candles = candles_from_prices(prices)
    script = {c.open_time: ("enter", f"{float(c.close) * 0.999:.2f}") for c in candles[::2]}
    risk = RiskConfig(
        risk_per_trade=d("0.05"), max_position_pct=d(position_pct), max_exposure_pct=d("1")
    )
    engine, store, _ = build_engine(
        ScriptedStrategy(script), bars_from(candles), {BTC: candles}, risk=risk
    )
    run(engine)
    assert engine.cash >= 0
    assert all(s.cash >= 0 for s in store.snapshots())
    for order in store.orders():
        if order.status is OrderStatus.REJECTED:
            assert order.reject_reason is not None
            assert order.reject_reason.startswith("insufficient_funds")


def test_pending_exit_does_not_consume_a_second_slot() -> None:
    flat = [("100", "101", "99", "100")] * 4
    btc = candles_from_prices(flat, BTC)
    eth = candles_from_prices([("10", "11", "9.5", "10")] * 4, ETH)
    ltc = candles_from_prices([("50", "51", "49", "50")] * 4, LTC)
    markets = {**MARKETS, LTC: market(LTC)}
    # T0: entra BTC. T0+2: BTC sale por señal mientras ETH y LTC piden entrar; hay 1 slot libre.
    strategy = MultiScriptedStrategy(
        {
            BTC: {T0: ("enter", "90"), T0 + 2 * H4: ("exit", None)},
            ETH: {T0 + 2 * H4: ("enter", "9")},
            LTC: {T0 + 2 * H4: ("enter", "45")},
        },
        strengths={(ETH, T0 + 2 * H4): 30.0, (LTC, T0 + 2 * H4): 10.0},
    )
    engine, store, _ = build_engine(
        strategy,
        bars_from(btc, eth, ltc),
        {BTC: btc, ETH: eth, LTC: ltc},
        risk=RiskConfig(max_positions=2),
        markets=markets,
    )
    run(engine)
    buys = [o for o in store.orders() if o.intent.side is Side.BUY and o.intent.pair != BTC]
    assert [o.intent.pair for o in buys] == [ETH]
    rejections = [
        e for e in store.events() if e.kind == "entry_rejected" and e.reason == "max_positions"
    ]
    assert len(rejections) == 1
    assert rejections[0].pair == LTC
    assert set(engine.positions.positions) == {ETH}


def test_trailing_at_or_above_close_sells_at_next_open() -> None:
    prices = [
        ("100", "101", "99", "100"),
        ("102", "104", "101", "103"),
        ("110", "112", "109", "111"),  # trailing propone 111 (= close) -> venta a mercado en t+1
        ("112", "113", "111", "112"),
    ]
    candles = candles_from_prices(prices)
    strategy = ScriptedStrategy({T0: ("enter", "90")}, trailing={T0 + 2 * H4: "111"})
    engine, store, broker = build_engine(strategy, bars_from(candles), {BTC: candles})
    run(engine)
    trade = store.trades()[0]
    assert trade.exit_reason is ExitReason.TRAILING
    assert trade.exit_time == T0 + 3 * H4  # open de t+1
    assert trade.exit_price == Decimal("111.94")  # 112 × 0.9995 = 111.944 -> 111.94
    assert broker.get_stop(BTC) is None
    assert engine.positions.get(BTC) is None


def test_unpublishable_stop_marks_unprotected_and_exit_retries_when_notional_recovers() -> None:
    # minNotional 900: la compra (10 × 100 = 1000) pasa, el stop (9.99 × 80 = 799) no.
    prices = [
        ("100", "101", "99", "100"),
        ("100", "101", "99", "100"),
        ("85", "86", "84", "85"),  # señal de salida: 9.99 × 85 = 849 < 900 -> STUCK
        ("95", "96", "94", "95"),  # sin señal nueva: el reintento pasa (9.99 × 95 = 949)
        ("95", "96", "94", "95"),
    ]
    candles = candles_from_prices(prices)
    markets = {BTC: market(BTC, min_notional="900"), ETH: market(ETH)}
    strategy = ScriptedStrategy({T0: ("enter", "80"), T0 + 2 * H4: ("exit", None)})
    engine, store, broker = build_engine(
        strategy,
        bars_from(candles),
        {BTC: candles},
        risk=RiskConfig(risk_per_trade=d("0.02")),
        markets=markets,
    )
    run(engine)
    kinds = [e.kind for e in store.events()]
    assert "stop_unpublishable" in kinds
    assert "exit_stuck" in kinds
    assert broker.get_stop(BTC) is None
    trades = store.trades()
    assert len(trades) == 1
    assert trades[0].exit_reason is ExitReason.SIGNAL
    assert trades[0].exit_time == T0 + 4 * H4  # reintento en t=3, fill al open de t=4
    assert engine.positions.get(BTC) is None
    assert BTC not in engine.stats.stuck_pairs


def test_exit_signal_then_gap_through_old_stop_sells_once_at_open() -> None:
    prices = [
        ("100", "101", "99", "100"),
        ("102", "104", "101", "103"),
        ("103", "104", "102", "103"),  # señal de salida: el stop (92.06) se cancela
        ("85", "86", "84", "85"),  # gap bajo el viejo stop: una sola venta al open
    ]
    candles = candles_from_prices(prices)
    strategy = ScriptedStrategy({T0: ("enter", "90"), T0 + 2 * H4: ("exit", None)})
    engine, store, _ = build_engine(strategy, bars_from(candles), {BTC: candles})
    run(engine)
    sells = [f for f in store.fills() if f.side is Side.SELL]
    assert len(sells) == 1
    assert sells[0].ref_price == Decimal("85")
    assert store.trades()[0].exit_reason is ExitReason.SIGNAL


def test_pending_exit_waits_for_missing_pair() -> None:
    btc = candles_from_prices(
        [
            ("100", "101", "99", "100"),
            ("102", "104", "101", "103"),
            ("103", "104", "102", "103"),
            ("110", "111", "109", "110"),
            ("120", "121", "119", "120"),
        ],
        BTC,
    )
    eth = candles_from_prices([("10", "11", "9.5", "10")] * 5, ETH)
    del btc[3]  # BTC falta en t=3: la venta espera
    strategy = ScriptedStrategy({T0: ("enter", "90"), T0 + 2 * H4: ("exit", None)})
    engine, store, _ = build_engine(strategy, bars_from(btc, eth), {BTC: btc, ETH: eth})
    run(engine)
    trade = store.trades()[0]
    assert trade.exit_time == T0 + 4 * H4
    assert trade.exit_price == Decimal("119.94")
    assert engine.positions.get(BTC) is None


def test_bnb_fee_on_sell_at_engine_level() -> None:
    prices = [
        ("100", "101", "99", "100"),
        ("100", "101", "99", "100"),
        ("100", "101", "99", "100"),
        ("110", "111", "109", "110"),
    ]
    candles = candles_from_prices(prices)
    execution = ExecutionConfig(pay_with_bnb=True, slippage_bps=Decimal("0"))
    strategy = ScriptedStrategy({T0: ("enter", "90"), T0 + 2 * H4: ("exit", None)})
    engine, store, _ = build_engine(
        strategy, bars_from(candles), {BTC: candles}, execution=execution
    )
    run(engine)
    sell = next(f for f in store.fills() if f.side is Side.SELL)
    assert sell.fee_asset == "USDT"
    assert sell.qty == Decimal("10")  # con BNB la compra no descontó base
    assert sell.fee_amount == Decimal("1100") * Decimal("0.00075")
    buy_fee = Decimal("1000") * Decimal("0.00075")
    expected = Decimal("10000") - Decimal("1000") - buy_fee + Decimal("1100") - sell.fee_amount
    assert engine.cash == expected
