"""Protecciones (ADR-0007) integradas en el loop del `Engine`: solo frenan entradas."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.fakes import (
    H4,
    MARKETS,
    MultiScriptedStrategy,
    Script,
    ScriptedStrategy,
    bars_from,
    build_engine,
    candles_from_prices,
)
from tests.factories import BTC, ETH, T0, d
from tradingbot.config.models import MarketFilterConfig, RiskConfig
from tradingbot.domain import ExitReason, Side
from tradingbot.persistence import TradeStore
from tradingbot.risk import KillSwitchState, ReasonCode
from tradingbot.risk.protections import MS_PER_DAY, PROTECTION_CLEARED, PROTECTION_TRIGGERED

DAY_START = T0 - T0 % MS_PER_DAY + MS_PER_DAY  # medianoche UTC siguiente a T0
FLAT60 = ("60", "61", "59", "60")
OFF = {"daily_loss_limit_pct": None, "max_drawdown_pct": None}


def rejections(store: TradeStore, reason: ReasonCode) -> int:
    return sum(1 for e in store.events() if e.kind == "entry_rejected" and e.reason == reason.value)


def protection_events(store: TradeStore, reason: ReasonCode) -> list[str]:
    return [
        e.kind
        for e in store.events()
        if e.kind in {PROTECTION_TRIGGERED, PROTECTION_CLEARED} and e.reason == reason.value
    ]


def test_daily_loss_blocks_entries_until_next_utc_day() -> None:
    # 6 velas de 4h en el mismo día UTC (00:00 → 23:59) y dos del día siguiente.
    prices = [
        ("100", "101", "99", "100"),  # 0: señal de entrada al close
        ("100", "100", "60", "60"),  # 1: fill al open 100 y caída del 40 % -> pérdida diaria
        FLAT60,  # 2: venta al open; nueva señal al close -> rechazada (mismo día)
        FLAT60,
        FLAT60,
        FLAT60,  # 5: última vela del día
        FLAT60,  # 6: día siguiente: nueva señal -> aceptada
        FLAT60,  # 7: fill al open
    ]
    candles = candles_from_prices(prices, start=DAY_START)
    t = [DAY_START + k * H4 for k in range(len(prices))]
    strategy = ScriptedStrategy(
        {t[0]: ("enter", "50"), t[1]: ("exit", None), t[2]: ("enter", "30"), t[6]: ("enter", "30")}
    )
    risk = RiskConfig(daily_loss_limit_pct=d("0.005"), max_drawdown_pct=None)
    engine, store, _ = build_engine(strategy, bars_from(candles), {BTC: candles}, risk=risk)
    for bar in bars_from(candles):
        engine.process_bar(bar)

    buys = [f for f in store.fills() if f.side is Side.BUY]
    assert [f.fill_ts for f in buys] == [t[1], t[7]]  # la señal del día bloqueado no se ejecuta
    assert rejections(store, ReasonCode.DAILY_LOSS_LIMIT) == 1
    assert protection_events(store, ReasonCode.DAILY_LOSS_LIMIT) == [
        PROTECTION_TRIGGERED,
        PROTECTION_CLEARED,
    ]
    assert engine.stats.protections[f"{PROTECTION_TRIGGERED}:daily_loss_limit"] == 1
    assert engine.stats.rejections[ReasonCode.DAILY_LOSS_LIMIT.value] == 1


class FakeSwitch:
    def __init__(self) -> None:
        self.state = KillSwitchState()

    def poll(self) -> KillSwitchState:
        return self.state


def test_kill_switch_flatten_sells_everything_and_blocks_entries() -> None:
    prices = [("100", "101", "99", "100")] * 6
    candles = candles_from_prices(prices)
    t = [T0 + k * H4 for k in range(len(prices))]
    strategy = ScriptedStrategy(
        {t[0]: ("enter", "90"), t[3]: ("enter", "90"), t[4]: ("enter", "90")}
    )
    switch = FakeSwitch()
    engine, store, _ = build_engine(
        strategy, bars_from(candles), {BTC: candles}, risk=RiskConfig(**OFF), kill_switch=switch
    )
    bars = bars_from(candles)
    engine.process_bar(bars[0])
    engine.process_bar(bars[1])  # fill de la compra al open
    assert engine.positions.get(BTC) is not None
    switch.state = KillSwitchState(active=True, flatten=True)
    engine.process_bar(bars[2])  # flatten -> venta pendiente
    engine.process_bar(bars[3])  # fill de la venta al open; la entrada se rechaza (kill switch)
    assert engine.positions.get(BTC) is None
    trades = store.trades()
    assert len(trades) == 1
    assert trades[0].exit_reason is ExitReason.FLATTEN
    assert trades[0].exit_client_order_id.endswith("-F")
    sells = [f for f in store.fills() if f.side is Side.SELL]
    assert [f.fill_ts for f in sells] == [t[3]]
    assert rejections(store, ReasonCode.KILL_SWITCH) == 1

    switch.state = KillSwitchState()
    engine.process_bar(bars[4])  # kill switch retirado: la entrada vuelve a pasar
    engine.process_bar(bars[5])
    assert engine.positions.get(BTC) is not None
    assert protection_events(store, ReasonCode.KILL_SWITCH) == [
        PROTECTION_TRIGGERED,
        PROTECTION_CLEARED,
    ]


def test_pair_cooldown_after_stop_through_engine() -> None:
    prices = [
        ("100", "101", "99", "100"),  # 0: entrada al close, stop a 10 de distancia
        ("100", "100", "85", "95"),  # 1: fill al open y stop tocado en la misma vela
        ("95", "96", "94", "95"),  # 2: señal rechazada (cooldown)
        ("95", "96", "94", "95"),  # 3: señal aceptada
        ("95", "96", "94", "95"),  # 4: fill al open
    ]
    candles = candles_from_prices(prices)
    t = [T0 + k * H4 for k in range(len(prices))]
    strategy = ScriptedStrategy(
        {t[0]: ("enter", "90"), t[1]: ("enter", "85"), t[2]: ("enter", "85"), t[3]: ("enter", "85")}
    )
    risk = RiskConfig(**OFF, cooldown_candles_after_stop=2)
    engine, store, _ = build_engine(strategy, bars_from(candles), {BTC: candles}, risk=risk)
    for bar in bars_from(candles):
        engine.process_bar(bar)

    trades = store.trades()
    assert [tr.exit_reason for tr in trades] == [ExitReason.STOP]
    buys = [f for f in store.fills() if f.side is Side.BUY]
    assert [f.fill_ts for f in buys] == [t[1], t[4]]
    assert engine.stats.rejections[ReasonCode.PAIR_COOLDOWN.value] == 2
    assert rejections(store, ReasonCode.PAIR_COOLDOWN) == 1  # mismo motivo seguido: un evento
    assert protection_events(store, ReasonCode.PAIR_COOLDOWN) == [
        PROTECTION_TRIGGERED,
        PROTECTION_CLEARED,
    ]
    assert all(e.pair == BTC for e in store.events() if e.reason == ReasonCode.PAIR_COOLDOWN.value)


def test_drawdown_halt_persists_without_auto_resume_until_manual_resume() -> None:
    prices = [
        ("100", "101", "99", "100"),  # 0: entrada al close
        ("100", "100", "60", "60"),  # 1: fill al open y caída -> DD 0.8 % > 0.5 %
        FLAT60,  # 2: venta al open; señal rechazada (halt)
        FLAT60,  # 3: en cash el DD no se mueve: sigue rechazada (sin auto_resume)
        FLAT60,  # 4: tras resume() manual la señal pasa
        FLAT60,  # 5: fill al open
    ]
    candles = candles_from_prices(prices)
    t = [T0 + k * H4 for k in range(len(prices))]
    strategy = ScriptedStrategy(
        {
            t[0]: ("enter", "50"),
            t[1]: ("exit", None),
            t[2]: ("enter", "30"),
            t[3]: ("enter", "30"),
            t[4]: ("enter", "30"),
        }
    )
    risk = RiskConfig(daily_loss_limit_pct=None, max_drawdown_pct=d("0.005"))
    engine, store, _ = build_engine(
        strategy, bars_from(candles), {BTC: candles}, risk=risk, auto_resume=False
    )
    bars = bars_from(candles)
    for bar in bars[:4]:
        engine.process_bar(bar)
    assert engine.risk.protections.drawdown_halted
    assert engine.stats.rejections[ReasonCode.DRAWDOWN_HALT.value] == 2
    assert rejections(store, ReasonCode.DRAWDOWN_HALT) == 1  # evento una vez, conteo dos
    engine.risk.protections.resume()
    for bar in bars[4:]:
        engine.process_bar(bar)
    buys = [f for f in store.fills() if f.side is Side.BUY]
    assert [f.fill_ts for f in buys] == [t[1], t[5]]
    assert protection_events(store, ReasonCode.DRAWDOWN_HALT) == [
        PROTECTION_TRIGGERED,
        PROTECTION_CLEARED,
    ]


def _path(moves: list[int]) -> list[tuple[str, str, str, str]]:
    price = 100.0
    prices = []
    for m in moves:
        open_ = price
        close = max(20.0, price + m)
        high = max(open_, close) + 1
        low = min(open_, close) - 1
        prices.append((f"{open_:.2f}", f"{high:.2f}", f"{low:.2f}", f"{close:.2f}"))
        price = close
    return prices


def _script(actions: list[str], prices: list[tuple[str, str, str, str]]) -> Script:
    script: dict[int, tuple[str, str | None]] = {}
    for i, action in enumerate(actions):
        if action == "enter":
            script[T0 + i * H4] = ("enter", f"{float(prices[i][3]) * 0.9:.2f}")
        elif action == "exit":
            script[T0 + i * H4] = ("exit", None)
    return script


@settings(max_examples=25, deadline=None)
@given(
    moves_btc=st.lists(st.integers(min_value=-9, max_value=9), min_size=8, max_size=30),
    moves_eth=st.lists(st.integers(min_value=-9, max_value=9), min_size=8, max_size=30),
    actions_btc=st.lists(st.sampled_from(["enter", "exit", "hold"]), min_size=8, max_size=30),
    actions_eth=st.lists(st.sampled_from(["enter", "exit", "hold"]), min_size=8, max_size=30),
    kill_at=st.integers(min_value=2, max_value=6),
)
def test_invariants_with_aggressive_protections(
    moves_btc: list[int],
    moves_eth: list[int],
    actions_btc: list[str],
    actions_eth: list[str],
    kill_at: int,
) -> None:
    n = min(len(moves_btc), len(moves_eth), len(actions_btc), len(actions_eth))
    btc_prices, eth_prices = _path(moves_btc[:n]), _path(moves_eth[:n])
    btc = candles_from_prices(btc_prices, pair=BTC)
    eth = candles_from_prices(eth_prices, pair=ETH)
    strategy = MultiScriptedStrategy(
        {BTC: _script(actions_btc[:n], btc_prices), ETH: _script(actions_eth[:n], eth_prices)}
    )
    risk = RiskConfig(
        max_positions=2,
        max_exposure_pct=d("0.5"),
        daily_loss_limit_pct=d("0.01"),
        max_drawdown_pct=d("0.03"),
        drawdown_pause_days=1,
        pause_after_consecutive_losses=2,
        pause_candles_after_losses=3,
        cooldown_candles_after_stop=2,
    )
    # Dos velas planas al final para que el flatten se llene; tienen que estar en la serie.
    last_btc, last_eth = btc_prices[-1][3], eth_prices[-1][3]
    tail_btc = candles_from_prices([(last_btc,) * 4] * 2, pair=BTC, start=T0 + n * H4)
    tail_eth = candles_from_prices([(last_eth,) * 4] * 2, pair=ETH, start=T0 + n * H4)
    btc_all, eth_all = [*btc, *tail_btc], [*eth, *tail_eth]
    switch = FakeSwitch()
    engine, store, _ = build_engine(
        strategy,
        bars_from(btc_all, eth_all),
        {BTC: btc_all, ETH: eth_all},
        risk=risk,
        kill_switch=switch,
    )
    for i, bar in enumerate(bars_from(btc_all, eth_all)):
        if i == n - kill_at:
            switch.state = KillSwitchState(active=True, flatten=True)  # flatten antes del final
        engine.process_bar(bar)

    assert engine.cash >= 0
    for snapshot in store.snapshots():
        assert snapshot.equity >= 0
        assert len({p.pair for p in snapshot.positions}) == len(snapshot.positions)
    for order in store.orders():
        intent = order.intent
        market = MARKETS[intent.pair]
        assert intent.qty >= market.min_qty
        assert intent.qty * intent.decision_price >= market.min_notional
    sells = [f for f in store.fills() if f.side is Side.SELL]
    assert len(store.trades()) == len(sells)
    # Con el kill switch en flatten y sin filtros que traben la venta, nada queda abierto.
    assert engine.positions.positions == {}
    assert engine.stats.stuck_pairs == set()
    exits_after_flatten = [tr for tr in store.trades() if tr.exit_reason is ExitReason.FLATTEN]
    assert all(tr.exit_client_order_id.endswith("-F") for tr in exits_after_flatten)


def test_rejection_events_dedupe_only_consecutive_signals() -> None:
    prices = [("100", "101", "99", "100")] * 5
    candles = candles_from_prices(prices)
    t = [T0 + k * H4 for k in range(len(prices))]
    # Señales en 0, 1 y 3 (la 2 no tiene): dos episodios distintos del mismo motivo.
    strategy = ScriptedStrategy(
        {t[0]: ("enter", "90"), t[1]: ("enter", "90"), t[3]: ("enter", "90")}
    )
    switch = FakeSwitch()
    switch.state = KillSwitchState(active=True)
    engine, store, _ = build_engine(
        strategy, bars_from(candles), {BTC: candles}, risk=RiskConfig(**OFF), kill_switch=switch
    )
    for bar in bars_from(candles):
        engine.process_bar(bar)
    assert engine.stats.rejections[ReasonCode.KILL_SWITCH.value] == 3
    assert rejections(store, ReasonCode.KILL_SWITCH) == 2  # 0 y 1 colapsan; 3 es un evento nuevo


def test_market_filter_blocks_entries_but_exits_execute() -> None:
    from tests.risk.test_market_filter import day_candles

    # Días 0-3 suben (filtro definido y habilitado al cerrar el día 3); el día 4 se desploma y al
    # cerrar su vela de las 20:00 el filtro se apaga: la salida del día 5 se ejecuta y la
    # re-entrada no.
    closes = ["100", "101", "102", "103", "80", "78"]
    candles = [c for day, close in enumerate(closes) for c in day_candles(day, close)]
    t = [c.open_time for c in candles]
    strategy = ScriptedStrategy(
        {t[23]: ("enter", "70"), t[30]: ("exit", None), t[32]: ("enter", "60")}
    )
    risk = RiskConfig(
        **OFF, market_filter=MarketFilterConfig(enabled=True, ema_days=3, momentum_days=2)
    )
    engine, store, _ = build_engine(strategy, bars_from(candles), {BTC: candles}, risk=risk)
    for bar in bars_from(candles):
        engine.process_bar(bar)

    buys = [f for f in store.fills() if f.side is Side.BUY]
    sells = [f for f in store.fills() if f.side is Side.SELL]
    assert [f.fill_ts for f in buys] == [t[24]]  # la entrada del día 3 se ejecuta al open del día 4
    assert [f.fill_ts for f in sells] == [t[31]]  # la salida por señal del día 5 se ejecuta
    assert rejections(store, ReasonCode.MARKET_FILTER) == 1  # la re-entrada del día 5 no pasa
    assert protection_events(store, ReasonCode.MARKET_FILTER) == [PROTECTION_TRIGGERED]
    assert engine.risk.protections.status()["market_filter"] == "deshabilitado"
