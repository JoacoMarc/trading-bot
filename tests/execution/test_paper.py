"""`PaperBroker` y `StopWatcher` (ADR-0011): fill al open en formación, stops entre cierres."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.engine.fakes import H4, MARKETS, ScriptedStrategy, bars_from, candles_from_prices
from tests.factories import BTC, T0, d, make_candle, make_intent
from tradingbot.config.models import ExecutionConfig, RiskConfig
from tradingbot.domain import Bar, Candle, ExitReason, OrderStatus, Pair, Side, Timeframe
from tradingbot.domain.errors import ExchangeUnavailable
from tradingbot.engine import Engine, PrecomputedSeries
from tradingbot.execution import PaperBroker, StopOrder, StopWatcher
from tradingbot.persistence import InMemoryStore
from tradingbot.risk import RiskManager

OFF = {"daily_loss_limit_pct": None, "max_drawdown_pct": None}


class FakePrices:
    def __init__(self, now_ms: int) -> None:
        self.now = now_ms
        self.last: dict[Pair, str] = {}
        self.forming: dict[Pair, Candle] = {}
        self.failures: list[Exception] = []
        self.calls: list[str] = []

    def now_ms(self) -> int:
        return self.now

    def fetch_last_price(self, pair: Pair) -> Decimal:
        self.calls.append(f"last:{pair.symbol}")
        if self.failures:
            raise self.failures.pop(0)
        return d(self.last[pair])

    def fetch_ohlcv_page(
        self, pair: Pair, timeframe: Timeframe, since_ms: int, limit: int = 1000
    ) -> list[Candle]:
        self.calls.append(f"klines:{pair.symbol}:{since_ms}")
        if self.failures:
            raise self.failures.pop(0)
        candle = self.forming.get(pair)
        return [candle] if candle is not None and candle.open_time >= since_ms else []


def broker(prices: FakePrices, **execution: object) -> PaperBroker:
    return PaperBroker(ExecutionConfig(**execution), MARKETS, prices, Timeframe.H4)


def test_fill_pending_at_forming_open_with_slippage_and_exchange_time() -> None:
    prices = FakePrices(now_ms=T0 + H4 + 4_000)  # 4 s después de abrir la vela t+1
    prices.forming[BTC] = make_candle(
        open_time=T0 + H4, open="102", high="103", low="101", close="102"
    )
    b = broker(prices)
    b.submit(make_intent(qty="2"), ts=T0 + H4 - 1)
    events = b.fill_pending(T0 + H4)
    assert len(events) == 1
    fill = events[0].fill
    assert fill is not None
    assert fill.ref_price == d("102")
    assert fill.price == d("102.06")  # 5 bps en contra, redondeado al tick hacia arriba
    assert fill.fill_ts == T0 + H4 + 4_000
    assert events[0].order.status is OrderStatus.FILLED
    assert b.pending_orders() == ()


def test_fill_pending_falls_back_to_last_price_when_candle_not_printed() -> None:
    prices = FakePrices(now_ms=T0 + H4 + 3_500)
    prices.last[BTC] = "101.5"  # la vela t+1 todavía no imprimió
    b = broker(prices, slippage_bps=Decimal("0"))
    b.submit(make_intent(qty="1"), ts=T0)
    fill = b.fill_pending(T0 + H4)[0].fill
    assert fill is not None
    assert fill.ref_price == d("101.5")
    assert fill.price == d("101.5")


def test_fill_pending_waits_on_exchange_error_and_next_bar_open_fills_it() -> None:
    prices = FakePrices(now_ms=T0 + H4 + 3_500)
    prices.failures = [ExchangeUnavailable("timeout")]
    b = broker(prices)
    b.submit(make_intent(qty="1"), ts=T0)
    assert b.fill_pending(T0 + H4) == []  # sin precio: la orden espera
    assert b.price_errors == 1
    assert len(b.pending_orders()) == 1
    bar = Bar.from_candles(candles_from_prices([("102", "104", "101", "103")], start=T0 + H4))
    events = b.on_bar_open(bar)  # el mismo open, cuatro horas después
    assert events[0].fill is not None
    assert events[0].fill.ref_price == d("102")


def test_fill_pending_rejects_buy_over_free_cash() -> None:
    prices = FakePrices(now_ms=T0 + H4 + 3_500)
    prices.last[BTC] = "100"
    b = broker(prices)
    b.bind_cash(lambda: d("150"))
    b.submit(make_intent(qty="2"), ts=T0)  # 200 USDT > 150 libres
    events = b.fill_pending(T0 + H4)
    assert events[0].fill is None
    assert events[0].order.status is OrderStatus.REJECTED
    assert "insufficient_funds" in (events[0].order.reject_reason or "")
    assert b.pending_orders() == ()


def test_check_stops_sells_at_last_price_when_touched() -> None:
    prices = FakePrices(now_ms=T0 + H4 + 7_200_000)  # a mitad de la vela t+1
    prices.last[BTC] = "89"
    b = broker(prices)
    b.set_stop(
        StopOrder(
            pair=BTC,
            stop_price=d("90"),
            qty=d("1"),
            exit_reason=ExitReason.STOP,
            strategy="ema_trend",
            signal_ts=T0,
        )
    )
    prices.last[BTC] = "95"
    assert b.check_stops() == []  # por encima del stop: nada
    prices.last[BTC] = "89"
    events = b.check_stops()
    assert len(events) == 1
    fill = events[0].fill
    assert fill is not None
    assert fill.side is Side.SELL
    assert fill.ref_price == d("89")
    assert fill.price == d("88.95")  # 5 bps en contra, redondeado hacia abajo
    assert fill.fill_ts == prices.now
    assert events[0].order.intent.exit_reason is ExitReason.STOP
    assert events[0].order.intent.client_order_id.endswith(f"-{(T0 + H4) // 1000}-X")
    assert b.get_stop(BTC) is None
    assert b.check_stops() == []  # sin stops no consulta precios
    assert prices.calls.count("last:BTC/USDT") == 2


def test_check_stops_skips_pair_on_exchange_error() -> None:
    prices = FakePrices(now_ms=T0 + H4)
    prices.last[BTC] = "80"
    prices.failures = [ExchangeUnavailable("timeout")]
    b = broker(prices)
    b.set_stop(StopOrder(BTC, d("90"), d("1"), ExitReason.TRAILING, "ema_trend", T0))
    assert b.check_stops() == []
    assert b.price_errors == 1
    assert b.get_stop(BTC) is not None  # el stop sigue en reposo
    assert len(b.check_stops()) == 1  # la siguiente pasada lo ejecuta


async def test_stop_watcher_ticks_until_stopped() -> None:
    prices = FakePrices(now_ms=T0 + H4)
    prices.last[BTC] = "80"
    b = broker(prices)
    b.set_stop(StopOrder(BTC, d("90"), d("1"), ExitReason.STOP, "ema_trend", T0))
    received: list[int] = []
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 3:
            watcher.stop()

    watcher = StopWatcher(b, 60, lambda events: received.append(len(events)), sleep=fake_sleep)
    await watcher.run()
    assert sleeps == [60, 60, 60]
    assert watcher.ticks == 2  # dos pasadas antes del stop
    assert received == [1]  # el stop se ejecutó una sola vez
    with pytest.raises(ValueError, match="positivo"):
        StopWatcher(b, 0, lambda _e: None)


def test_engine_applies_paper_fills_and_watcher_stops_outside_the_bar_loop() -> None:
    # Entrada al cierre de la vela 0 -> fill inmediato al open de la vela 1; el watcher vende
    # cuando el último precio toca el stop, y el Engine cierra el trade en el acto.
    candles = candles_from_prices([("100", "101", "99", "100"), ("100", "101", "95", "96")])
    strategy = ScriptedStrategy({T0: ("enter", "90")})
    prices = FakePrices(now_ms=T0 + H4 + 5_000)
    prices.forming[BTC] = make_candle(
        open_time=T0 + H4, open="100", high="101", low="95", close="96"
    )
    store = InMemoryStore()
    exec_cfg = ExecutionConfig(slippage_bps=Decimal("0"))
    risk_cfg = RiskConfig(**OFF)
    b = PaperBroker(exec_cfg, MARKETS, prices, Timeframe.H4)
    engine = Engine(
        strategy=strategy,
        feed=_NoFeed(),
        series=PrecomputedSeries(strategy, {BTC: candles}),
        broker=b,
        risk=RiskManager(risk_cfg, exec_cfg, MARKETS, strategy.name),
        store=store,
        markets=MARKETS,
        execution=exec_cfg,
        initial_cash=d("10000"),
    )
    bars = bars_from(candles)
    engine.process_bar(bars[0])
    assert len(b.pending_orders()) == 1
    engine.apply_events(b.fill_pending(T0 + H4))
    position = engine.positions.get(BTC)
    assert position is not None
    assert position.entry_price == d("100")
    assert b.get_stop(BTC) is not None  # el stop protege la posición desde el fill
    assert engine.cash < d("10000")

    prices.now = T0 + H4 + 3_600_000
    prices.last[BTC] = "89.5"
    watcher = StopWatcher(b, 60, engine.apply_events)
    assert len(watcher.tick()) == 1
    assert engine.positions.get(BTC) is None
    trades = store.trades()
    assert len(trades) == 1
    assert trades[0].exit_reason is ExitReason.STOP
    assert trades[0].exit_price == d("89.5")
    assert trades[0].exit_time == prices.now
    # Al cierre de la vela 1 no hay stop en reposo ni posición: la regla de gap no dispara nada.
    engine.process_bar(bars[1])
    assert store.trades() == trades


class _NoFeed:
    timeframe = Timeframe.H4
    pairs = (BTC,)

    def warmup_bars(self) -> list[Bar]:
        return []

    def __aiter__(self):  # type: ignore[no-untyped-def]
        raise NotImplementedError


def test_bars_since_exit_matches_backtest_when_fill_arrives_outside_the_bar_loop() -> None:
    # Backtest: venta decidida al cierre de t1 se llena al open de t2 y en t2 la estrategia ve
    # bars_since_exit = 0. Paper: el mismo fill llega enseguida (fill_pending) y debe dar 0 igual.
    prices = [("100", "101", "99", "100")] * 4
    candles = candles_from_prices(prices)
    bars = bars_from(candles)
    t = [c.open_time for c in candles]
    strategy = ScriptedStrategy({t[0]: ("enter", "90"), t[1]: ("exit", None)})
    prices_src = FakePrices(now_ms=T0 + 5_000)
    prices_src.last[BTC] = "100"
    exec_cfg = ExecutionConfig(slippage_bps=Decimal("0"))
    b = PaperBroker(exec_cfg, MARKETS, prices_src, Timeframe.H4)
    engine = Engine(
        strategy=strategy,
        feed=_NoFeed(),
        series=PrecomputedSeries(strategy, {BTC: candles}),
        broker=b,
        risk=RiskManager(RiskConfig(**OFF), exec_cfg, MARKETS, strategy.name),
        store=InMemoryStore(),
        markets=MARKETS,
        execution=exec_cfg,
        initial_cash=d("10000"),
    )
    for i in range(3):
        engine.process_bar(bars[i])
        prices_src.now = t[i + 1] + 5_000  # 5 s después de abrir la vela siguiente
        engine.apply_events(b.fill_pending(t[i + 1]))
    seen = {open_time: since for _pair, open_time, since, _pos in strategy.seen}
    assert seen[t[2]] == 0  # igual que el backtest (tests/engine/test_engine.py)
    assert seen[t[1]] is None


def test_replay_fill_is_dated_at_the_historical_candle() -> None:
    prices = FakePrices(now_ms=T0 + 3 * H4 + 5_000)  # tres velas después: reposición
    prices.forming[BTC] = make_candle(
        open_time=T0 + H4, open="102", high="103", low="101", close="102"
    )
    b = broker(prices, slippage_bps=Decimal("0"))
    b.submit(make_intent(qty="1"), ts=T0)
    fill = b.fill_pending(T0 + H4)[0].fill
    assert fill is not None
    assert fill.ref_price == d("102")
    assert fill.fill_ts == T0 + H4  # la vela ya cerró: se fecha en su open_time, no en `ahora`
