"""Dobles de prueba del motor: feed en memoria, estrategia guionada y mercados fijos."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Mapping, Sequence
from decimal import Decimal

from tests.factories import BTC, ETH, T0, d, make_candle
from tradingbot.config.models import ExecutionConfig, RiskConfig
from tradingbot.domain import Bar, Candle, ExitReason, Pair, Signal, SignalAction, Timeframe
from tradingbot.engine import Engine, PrecomputedSeries
from tradingbot.exchange.binance import MarketInfo
from tradingbot.execution import SimulatedBroker
from tradingbot.indicators import FloatArray
from tradingbot.persistence import InMemoryStore
from tradingbot.risk import RiskManager
from tradingbot.strategy import OhlcvArrays, Strategy, StrategyContext, StrategyParams

H4 = Timeframe.H4.ms


def market(pair: Pair = BTC, min_notional: str = "5") -> MarketInfo:
    return MarketInfo(
        pair=pair,
        tick_size=d("0.01"),
        step_size=d("0.00001"),
        min_qty=d("0.00001"),
        max_qty=None,
        min_notional=d(min_notional),
    )


MARKETS: dict[Pair, MarketInfo] = {BTC: market(BTC), ETH: market(ETH)}


class ListFeed:
    """`MarketFeed` que emite bars ya construidos, sin warmup."""

    def __init__(self, bars: Sequence[Bar], timeframe: Timeframe = Timeframe.H4) -> None:
        self._bars = list(bars)
        self._timeframe = timeframe

    @property
    def timeframe(self) -> Timeframe:
        return self._timeframe

    @property
    def pairs(self) -> tuple[Pair, ...]:
        seen: set[Pair] = set()
        for bar in self._bars:
            seen.update(bar.pairs)
        return tuple(sorted(seen))

    def warmup_bars(self) -> list[Bar]:
        return []

    async def __aiter__(self) -> AsyncIterator[Bar]:
        for bar in self._bars:
            yield bar


Script = Mapping[int, tuple[str, str | None]]  # open_time -> ("enter", stop) | ("exit", None)


class ScriptedStrategy(Strategy):
    """Emite señales fijas por `open_time`; `trailing` es un mapa open_time -> nivel."""

    name = "scripted_tst"
    Params = StrategyParams

    def __init__(
        self,
        script: Script | None = None,
        trailing: Mapping[int, str] | None = None,
        strengths: Mapping[int, float] | None = None,
    ) -> None:
        super().__init__(StrategyParams())
        self.script = dict(script or {})
        self.trailing = {k: d(v) for k, v in (trailing or {}).items()}
        self.strengths = dict(strengths or {})
        self.seen: list[
            tuple[Pair, int, int | None, bool]
        ] = []  # (pair, open_time, bars_since_exit, has_position)

    @property
    def longest_period(self) -> int:
        return 1

    def compute_indicators(self, ohlcv: OhlcvArrays) -> dict[str, FloatArray]:
        return {}

    def on_candle(self, ctx: StrategyContext) -> Signal:
        self.seen.append((ctx.pair, ctx.open_time, ctx.bars_since_exit, ctx.position is not None))
        action = self.script.get(ctx.open_time)
        if action is None:
            return Signal.hold(ctx.pair, ctx.open_time)
        kind, stop = action
        if kind == "enter":
            return Signal(
                action=SignalAction.ENTER_LONG,
                pair=ctx.pair,
                open_time=ctx.open_time,
                stop_price=d(stop or "0"),
                strength=self.strengths.get(ctx.open_time, 25.0),
            )
        return Signal(
            action=SignalAction.EXIT_LONG,
            pair=ctx.pair,
            open_time=ctx.open_time,
            exit_reason=ExitReason.SIGNAL,
        )

    def trailing_stop(self, ctx: StrategyContext) -> Decimal | None:
        return self.trailing.get(ctx.open_time)


class MultiScriptedStrategy(ScriptedStrategy):
    """Como `ScriptedStrategy` pero con un guion por par: `{pair: {open_time: acción}}`."""

    name = "multiscript_t"

    def __init__(
        self,
        scripts: Mapping[Pair, Script],
        strengths: Mapping[tuple[Pair, int], float] | None = None,
    ) -> None:
        super().__init__()
        self.scripts = {pair: dict(script) for pair, script in scripts.items()}
        self.pair_strengths = dict(strengths or {})

    def on_candle(self, ctx: StrategyContext) -> Signal:
        self.script = self.scripts.get(ctx.pair, {})
        self.strengths = {t: s for (pair, t), s in self.pair_strengths.items() if pair == ctx.pair}
        return super().on_candle(ctx)


def candles_from_prices(
    prices: Iterable[tuple[str, str, str, str]], pair: Pair = BTC, start: int = T0
) -> list[Candle]:
    """(open, high, low, close) por vela, consecutivas desde `start`."""
    return [
        make_candle(pair=pair, open_time=start + i * H4, open=o, high=h, low=lo, close=c)
        for i, (o, h, lo, c) in enumerate(prices)
    ]


def bars_from(*series: Sequence[Candle]) -> list[Bar]:
    by_time: dict[int, list[Candle]] = {}
    for candles in series:
        for candle in candles:
            by_time.setdefault(candle.open_time, []).append(candle)
    return [Bar.from_candles(by_time[t]) for t in sorted(by_time)]


def build_engine(
    strategy: Strategy,
    bars: Sequence[Bar],
    candles_by_pair: Mapping[Pair, Sequence[Candle]],
    *,
    cash: str = "10000",
    risk: RiskConfig | None = None,
    execution: ExecutionConfig | None = None,
    markets: Mapping[Pair, MarketInfo] | None = None,
) -> tuple[Engine, InMemoryStore, SimulatedBroker]:
    risk_cfg = risk or RiskConfig()
    exec_cfg = execution or ExecutionConfig()
    mkts = dict(markets or MARKETS)
    store = InMemoryStore()
    broker = SimulatedBroker(exec_cfg, mkts)
    engine = Engine(
        strategy=strategy,
        feed=ListFeed(bars),
        series=PrecomputedSeries(strategy, candles_by_pair),
        broker=broker,
        risk=RiskManager(risk_cfg, exec_cfg, mkts, strategy.name),
        store=store,
        markets=mkts,
        execution=exec_cfg,
        initial_cash=d(cash),
    )
    return engine, store, broker
