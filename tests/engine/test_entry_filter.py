"""Un fallo del predictor nunca impide proteger o vender posiciones."""

import asyncio
from collections.abc import Mapping

from tests.engine.fakes import H4, ScriptedStrategy, bars_from, build_engine, candles_from_prices
from tests.factories import BTC, T0
from tradingbot.domain import Pair, Signal
from tradingbot.prediction.base import EntryDecision
from tradingbot.strategy.base import StrategyContext


class Filter:
    fail = False
    accept = True

    def observe(self, contexts: Mapping[Pair, StrategyContext], signal_ts: int) -> None:
        if self.fail:
            raise ValueError("modelo roto")

    def evaluate(self, signal: Signal, signal_ts: int) -> EntryDecision:
        assert signal_ts == signal.open_time + H4
        return EntryDecision(self.accept, "veto")


def test_accept_all_matches_no_filter_and_failure_does_not_block_exit() -> None:
    candles = candles_from_prices([("100", "101", "99", "100")] * 5)
    commands = {T0: ("enter", "90"), T0 + 2 * H4: ("exit", None)}
    control, control_store, _ = build_engine(
        ScriptedStrategy(commands), bars_from(candles), {BTC: candles}
    )
    asyncio.run(control.run())
    engine, store, _ = build_engine(ScriptedStrategy(commands), bars_from(candles), {BTC: candles})
    gate = Filter()
    engine.entry_filter = gate
    for n, bar in enumerate(bars_from(candles)):
        gate.fail = n >= 2
        engine.process_bar(bar)
    assert store.fills() == control_store.fills()
    assert engine.cash == control.cash
    assert len(store.trades()) == 1


def test_veto_blocks_only_entries() -> None:
    candles = candles_from_prices([("100", "101", "99", "100")] * 3)
    engine, store, _ = build_engine(
        ScriptedStrategy({T0: ("enter", "90")}), bars_from(candles), {BTC: candles}
    )
    gate = Filter()
    gate.accept = False
    engine.entry_filter = gate
    asyncio.run(engine.run())
    assert not store.fills()
    assert engine.stats.rejections["veto"] == 1
