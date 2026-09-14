"""Cablea config → datos → estrategia → `Engine` → métricas → artefactos registrados.

Un backtest es el mismo `Engine` de paper/live alimentado por `HistoricalFeed`, con
`SimulatedBroker` e `InMemoryStore`. Los benchmarks buy & hold se calculan sobre las mismas velas
del rango. Toda corrida se registra en `experiments/` (regla dura 6) salvo que se pida lo contrario.
"""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from tradingbot.backtest.benchmark import (
    BenchmarkResult,
    buy_and_hold,
    equal_weights,
    gated_hold,
)
from tradingbot.backtest.metrics import EquityPoint, Metrics, compute_metrics
from tradingbot.backtest.report import (
    ReportContext,
    equity_csv,
    plot_equity,
    render_report,
    trades_csv,
)
from tradingbot.config.models import BacktestConfig, RiskConfig, StrategyConfig
from tradingbot.config.settings import BotConfig
from tradingbot.data.feeds import HistoricalFeed
from tradingbot.data.store import ParquetStore
from tradingbot.domain.candle import Candle
from tradingbot.domain.errors import ConfigError, DataError
from tradingbot.domain.orders import Fill
from tradingbot.domain.pair import Pair
from tradingbot.domain.positions import Trade
from tradingbot.engine.engine import Engine, EngineResult
from tradingbot.engine.series import PrecomputedSeries
from tradingbot.exchange.binance import MarketInfo, load_markets_snapshot
from tradingbot.execution.simulated import SimulatedBroker
from tradingbot.persistence.experiments import (
    ExperimentMeta,
    RunArtifacts,
    build_meta,
    next_run_id,
    write_run,
)
from tradingbot.persistence.store import EventRecord, InMemoryStore
from tradingbot.risk.manager import RiskManager
from tradingbot.risk.market_filter import MarketFilter
from tradingbot.strategy.base import Strategy
from tradingbot.strategy.registry import build_strategy, effective_warmup

BenchmarkKind = Literal["bh_btc", "equal_weight"]
BTC_USDT = Pair(base="BTC", quote="USDT")


def date_to_ms(value: date) -> int:
    return int(datetime(value.year, value.month, value.day, tzinfo=UTC).timestamp() * 1000)


def ms_to_date(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).date().isoformat()


@dataclass(frozen=True, slots=True)
class RunPayload:
    """Todo lo que hace falta para escribir los artefactos de una corrida (backtest o benchmark)."""

    label: str
    title: str
    strategy_name: str
    spec_path: str | None
    params: Mapping[str, Any]
    config_dump: Mapping[str, Any]
    metrics: Metrics
    benchmarks: Mapping[str, Metrics]
    equity: Sequence[EquityPoint]
    benchmark_equities: Mapping[str, Sequence[EquityPoint]]
    trades: Sequence[Trade]
    fills: Sequence[Fill]
    events: Sequence[EventRecord]
    data_line: str
    costs_line: str
    risk_line: str
    meta: ExperimentMeta


@dataclass(frozen=True, slots=True)
class BacktestRun:
    config: BotConfig
    strategy: Strategy
    engine_result: EngineResult
    metrics: Metrics
    benchmarks: dict[str, BenchmarkResult]
    equity: list[EquityPoint]
    start_ms: int
    end_ms: int
    warmup: int
    duration_s: float
    data_files: list[Path]
    markets: dict[Pair, MarketInfo]
    activation: dict[Pair, int] = field(default_factory=dict)  # pares activados tarde
    inactive: tuple[Pair, ...] = ()  # pares sin velas suficientes en el rango

    @property
    def trades(self) -> tuple[Trade, ...]:
        return self.engine_result.store.trades()

    @property
    def fills(self) -> tuple[Fill, ...]:
        return self.engine_result.store.fills()

    @property
    def events(self) -> tuple[EventRecord, ...]:
        return self.engine_result.store.events()


# ------------------------------------------------------------------ armado


def load_markets_for(
    pairs: Sequence[Pair], markets: Mapping[Pair, MarketInfo] | None
) -> dict[Pair, MarketInfo]:
    source = dict(markets) if markets is not None else load_markets_snapshot().by_pair()
    missing = [p.symbol for p in pairs if p not in source]
    if missing:
        msg = (
            f"sin MarketInfo para {', '.join(missing)}; correr "
            "`tradingbot data-markets --refresh --update-snapshot`"
        )
        raise ConfigError(msg)
    return {p: source[p] for p in pairs}


def resolve_range(config: BotConfig, store: ParquetStore, warmup: int) -> tuple[int, int]:
    """`[start_ms, end_ms)` del backtest: config o, si falta, lo que permitan datos y warmup.

    Sin `start` en la config arranca con el primer par que completa su warmup; los demás se
    activan cuando completan el suyo (ADR-0008).
    """
    pairs = config.strategy.pairs
    timeframe = config.strategy.timeframe
    starts: list[int] = []
    ends: list[int] = []
    for pair in pairs:
        info = store.info(pair, timeframe)
        if info is None:
            msg = (
                f"sin datos de {pair} {timeframe.value} en {store.exchange_dir}; "
                "correr download-data"
            )
            raise DataError(msg)
        starts.append(info.first_open_time + warmup * timeframe.ms)
        ends.append(info.last_open_time + timeframe.ms)
    start_ms = date_to_ms(config.backtest.start) if config.backtest.start else min(starts)
    effective_end = config.backtest.effective_end
    end_ms = date_to_ms(effective_end) if effective_end else min(ends)
    end_ms = min(end_ms, min(ends))
    if end_ms <= start_ms:
        msg = f"rango vacío: start {ms_to_date(start_ms)} >= end {ms_to_date(end_ms)}"
        raise ConfigError(msg)
    return start_ms, end_ms


def _range_candles(feed: HistoricalFeed, pair: Pair) -> list[Candle]:
    return [c for c in (bar.get(pair) for bar in feed.iter_bars()) if c is not None]


GATED_BENCHMARK = "B&H BTC filtrado"


def market_filter_states(
    config: BotConfig,
    warmup: Sequence[Candle],
    candles: Sequence[Candle],
) -> list[bool]:
    """Estado del filtro de mercado al cierre de cada vela del rango (sembrado con el warmup)."""
    market_filter = MarketFilter(config.risk.market_filter)
    for candle in warmup:
        market_filter.on_candle(candle)
    states: list[bool] = []
    for candle in candles:
        market_filter.on_candle(candle)
        states.append(market_filter.enabled)
    return states


def _compute_benchmarks(
    config: BotConfig,
    candles_by_pair: Mapping[Pair, Sequence[Candle]],
    markets: Mapping[Pair, MarketInfo],
    warmup_by_pair: Mapping[Pair, Sequence[Candle]] | None = None,
) -> dict[str, BenchmarkResult]:
    results: dict[str, BenchmarkResult] = {}
    pairs = [p for p in config.strategy.pairs if candles_by_pair.get(p)]
    if not pairs:
        return results
    reference = BTC_USDT if candles_by_pair.get(BTC_USDT) else pairs[0]
    results[f"B&H {reference.base}"] = buy_and_hold(
        "bh",
        {reference: candles_by_pair[reference]},
        {reference: Decimal(1)},
        config.backtest.initial_cash,
        config.execution,
        markets,
    )
    if len(pairs) > 1:
        results["Equiponderado"] = buy_and_hold(
            "eq",
            candles_by_pair,
            equal_weights(pairs),
            config.backtest.initial_cash,
            config.execution,
            markets,
        )
    filter_cfg = config.risk.market_filter
    if filter_cfg.enabled and candles_by_pair.get(filter_cfg.reference_pair):
        reference = filter_cfg.reference_pair
        warmup = (warmup_by_pair or {}).get(reference, ())
        results[GATED_BENCHMARK] = gated_hold(
            "bhf",
            candles_by_pair[reference],
            market_filter_states(config, warmup, candles_by_pair[reference]),
            config.backtest.initial_cash,
            config.execution,
            markets[reference],
        )
    return results


def load_candles(config: BotConfig, end_ms: int | None = None) -> dict[Pair, list[Candle]]:
    """Velas completas por par hasta `end_ms` (o fin del holdout excluido): caché para WF/optuna."""
    store = ParquetStore(config.data.data_dir)
    if end_ms is None:
        strategy = build_strategy(config.strategy)
        _, end_ms = resolve_range(config, store, effective_warmup(config.strategy, strategy))
    return {
        pair: store.read_candles(pair, config.strategy.timeframe, None, end_ms)
        for pair in config.strategy.pairs
    }


def derive_config(
    config: BotConfig,
    *,
    params: Mapping[str, Any] | None = None,
    start: date | None = None,
    end: date | None = None,
) -> BotConfig:
    """Copia de la config con otros parámetros de estrategia y/o rango (walk-forward, optuna)."""
    strategy = config.strategy
    if params is not None:
        # model_validate y no model_copy: que un start >= end o un parámetro inválido sea una
        # ValidationError (trial fallido) y no un ValueError a mitad del walk-forward.
        strategy = StrategyConfig.model_validate(
            {**strategy.model_dump(mode="json"), "params": {**strategy.params, **params}}
        )
    backtest = config.backtest
    changes: dict[str, Any] = {}
    if start is not None:
        changes["start"] = start
    if end is not None:
        changes["end"] = end
    if changes:
        backtest = BacktestConfig.model_validate(
            {**backtest.model_dump(mode="json"), **{k: v.isoformat() for k, v in changes.items()}}
        )
    return config.model_copy(update={"strategy": strategy, "backtest": backtest})


def run_backtest(
    config: BotConfig,
    *,
    markets: Mapping[Pair, MarketInfo] | None = None,
    with_benchmarks: bool = True,
    candles: Mapping[Pair, Sequence[Candle]] | None = None,
) -> BacktestRun:
    """Un backtest con el Engine único. `candles` evita releer parquet (walk-forward, optuna)."""
    started = time.perf_counter()
    strategy = build_strategy(config.strategy)
    warmup = effective_warmup(config.strategy, strategy)
    pairs = list(config.strategy.pairs)
    timeframe = config.strategy.timeframe
    market_infos = load_markets_for(pairs, markets)
    store = ParquetStore(config.data.data_dir)
    start_ms, end_ms = resolve_range(config, store, warmup)
    feed = HistoricalFeed(
        None if candles is not None else store,
        pairs,
        timeframe,
        start_ms,
        end_ms,
        warmup=warmup,
        candles=candles,
        late_pairs="activate",
    )

    range_candles = {pair: _range_candles(feed, pair) for pair in pairs}
    series_candles = {pair: [*feed.warmup_candles(pair), *range_candles[pair]] for pair in pairs}
    series = PrecomputedSeries(strategy, series_candles)
    trade_store = InMemoryStore()
    engine = Engine(
        strategy=strategy,
        feed=feed,
        series=series,
        broker=SimulatedBroker(config.execution, market_infos),
        risk=RiskManager(
            config.risk,
            config.execution,
            market_infos,
            strategy.name,
            auto_resume=True,  # un backtest siempre reanuda solo (ADR-0007), sea cual sea `mode`
        ),
        store=trade_store,
        markets=market_infos,
        execution=config.execution,
        initial_cash=config.backtest.initial_cash,
    )
    result = asyncio.run(engine.run())

    snapshots = trade_store.snapshots()
    equity = [(s.ts, s.equity) for s in snapshots]
    invested = [len(s.positions) > 0 for s in snapshots]
    metrics = compute_metrics(equity, invested, trade_store.trades(), trade_store.fills())
    benchmarks = (
        _compute_benchmarks(
            config,
            range_candles,
            market_infos,
            {pair: feed.warmup_candles(pair) for pair in pairs},
        )
        if with_benchmarks
        else {}
    )
    return BacktestRun(
        config=config,
        strategy=strategy,
        engine_result=result,
        metrics=metrics,
        benchmarks=benchmarks,
        equity=equity,
        start_ms=start_ms,
        end_ms=end_ms,
        warmup=warmup,
        duration_s=time.perf_counter() - started,
        data_files=[store.path(p, timeframe) for p in pairs],
        markets=market_infos,
        activation=feed.activation_times,
        inactive=feed.inactive_pairs,
    )


def run_benchmark(
    config: BotConfig, kind: BenchmarkKind, *, markets: Mapping[Pair, MarketInfo] | None = None
) -> tuple[BenchmarkResult, BotConfig, int, int, list[Path]]:
    """Benchmark buy & hold como corrida propia (EXP-0001 / EXP-0002)."""
    strategy = build_strategy(config.strategy)
    warmup = effective_warmup(config.strategy, strategy)
    pairs = list(config.strategy.pairs)
    timeframe = config.strategy.timeframe
    market_infos = load_markets_for(pairs, markets)
    store = ParquetStore(config.data.data_dir)
    start_ms, end_ms = resolve_range(config, store, warmup)
    candles = {p: store.read_candles(p, timeframe, start_ms, end_ms) for p in pairs}
    if kind == "bh_btc":
        reference = BTC_USDT if BTC_USDT in candles else pairs[0]
        result = buy_and_hold(
            "bh",
            {reference: candles[reference]},
            {reference: Decimal(1)},
            config.backtest.initial_cash,
            config.execution,
            market_infos,
        )
    else:
        result = buy_and_hold(
            "eq",
            candles,
            equal_weights(pairs),
            config.backtest.initial_cash,
            config.execution,
            market_infos,
        )
    return result, config, start_ms, end_ms, [store.path(p, timeframe) for p in pairs]


# ------------------------------------------------------------------ registro


def costs_line(config: BotConfig) -> str:
    fee = config.execution.effective_fee_rate * 100
    where = "en quote (BNB)" if config.execution.pay_with_bnb else "en el activo recibido"
    return f"fee {fee:.3f} % {where}, slippage {config.execution.slippage_bps} bps"


def risk_line(config: BotConfig) -> str:
    r = config.risk
    base = (
        f"riesgo/trade {r.risk_per_trade * 100:.2f} %, "
        f"tope {r.max_position_pct * 100:.0f} % del cash por posición, "
        f"máx. {r.max_positions} posiciones, "
        f"exposición máx. {r.max_exposure_pct * 100:.0f} %"
    )
    return f"{base} · protecciones: {', '.join(_protections_summary(r))}"


def _pct_short(value: Decimal) -> str:
    """`20 %`, `2.5 %`: un decimal solo cuando hace falta."""
    text = f"{value * 100:.1f}"
    return f"{text[:-2] if text.endswith('.0') else text} %"


def _protections_summary(r: RiskConfig) -> list[str]:
    """Una frase por protección (ADR-0007), `off` cuando está desactivada."""
    daily = (
        "pérdida diaria off"
        if r.daily_loss_limit_pct is None
        else f"pérdida diaria {r.daily_loss_limit_pct * 100:.1f} % (día UTC)"
    )
    resume = r.effective_drawdown_resume_pct
    if r.max_drawdown_pct is None or resume is None:
        drawdown = "circuit breaker off"
    else:
        pause = "" if r.drawdown_pause_days is None else f" o tras {r.drawdown_pause_days} d"
        drawdown = (
            f"circuit breaker DD {_pct_short(r.max_drawdown_pct)} "
            f"(reanuda bajo {_pct_short(resume)}{pause})"
        )
    losses = (
        "pausa por pérdidas off"
        if r.pause_after_consecutive_losses is None
        else (
            f"pausa {r.pause_candles_after_losses} velas tras "
            f"{r.pause_after_consecutive_losses} pérdidas seguidas"
        )
    )
    cooldown = (
        "cooldown tras stop off"
        if r.cooldown_candles_after_stop == 0
        else f"cooldown tras stop {r.cooldown_candles_after_stop} velas"
    )
    mf = r.market_filter
    market = (
        "filtro de mercado off"
        if not mf.enabled
        else (
            f"filtro de mercado {mf.pair} (cierre diario > {mf.average.upper()}{mf.ema_days} "
            f"y retorno {mf.momentum_days} d > 0"
            f"{', solo benchmark' if mf.benchmark_only else ''})"
        )
    )
    return [daily, drawdown, losses, cooldown, market]


def data_line(
    config: BotConfig,
    start_ms: int,
    end_ms: int,
    warmup: int,
    data_hash: str,
    activation: Mapping[Pair, int] | None = None,
    inactive: Sequence[Pair] = (),
) -> str:
    holdout = "incluye holdout" if config.backtest.include_holdout else "sin holdout"
    pairs = ", ".join(p.symbol for p in config.strategy.pairs)
    line = (
        f"binance {config.strategy.timeframe.value} {ms_to_date(start_ms)} → {ms_to_date(end_ms)} "
        f"({holdout}), warmup {warmup} velas, pares {pairs}, hash {data_hash}"
    )
    if activation:
        late = ", ".join(
            f"{p.symbol} desde {ms_to_date(t)}"
            for p, t in sorted(activation.items(), key=lambda kv: kv[1])
        )
        line = f"{line}; activación tardía: {late}"
    if inactive:
        line = f"{line}; sin velas suficientes: {', '.join(p.symbol for p in inactive)}"
    return line


def frozen_config(config: BotConfig, start_ms: int, end_ms: int) -> dict[str, Any]:
    """Config pública con el rango **efectivo** fijado: recargarla reproduce la corrida aunque
    después se descarguen más velas (ADR-0006)."""
    dump = config.public_dump()
    dump["backtest"]["start"] = ms_to_date(start_ms)
    dump["backtest"]["end"] = ms_to_date(end_ms)
    return dump


def spec_path(strategy_name: str, root: Path) -> str | None:
    """Última spec `docs/strategy/<nombre>-vN.md` disponible, relativa a la raíz."""
    slug = strategy_name.replace("_", "-")
    candidates = sorted((root / "docs" / "strategy").glob(f"{slug}-v*.md"))
    return candidates[-1].relative_to(root).as_posix() if candidates else None


def payload_from_backtest(run: BacktestRun, root: Path, label: str | None = None) -> RunPayload:
    config = run.config
    meta = build_meta(
        strategy=run.strategy.name,
        timeframe=config.strategy.timeframe.value,
        pairs=[p.symbol for p in config.strategy.pairs],
        start=ms_to_date(run.start_ms),
        end=ms_to_date(run.end_ms),
        include_holdout=config.backtest.include_holdout,
        params=run.strategy.params.model_dump(mode="json"),
        data_files=run.data_files,
        duration_s=run.duration_s,
        root=root,
        extra={"warmup": run.warmup, "bars": run.engine_result.stats.bars},
    )
    return RunPayload(
        label=label or f"{run.strategy.name}-{config.strategy.timeframe.value}",
        title=f"{run.strategy.name} {config.strategy.timeframe.value}",
        strategy_name=run.strategy.name,
        spec_path=spec_path(run.strategy.name, root),
        params=run.strategy.params.model_dump(mode="json"),
        config_dump=frozen_config(config, run.start_ms, run.end_ms),
        metrics=run.metrics,
        benchmarks={k: v.metrics for k, v in run.benchmarks.items()},
        equity=run.equity,
        benchmark_equities={k: v.equity for k, v in run.benchmarks.items()},
        trades=run.trades,
        fills=run.fills,
        events=run.events,
        data_line=data_line(
            config,
            run.start_ms,
            run.end_ms,
            run.warmup,
            meta.data_hash,
            run.activation,
            run.inactive,
        ),
        costs_line=costs_line(config),
        risk_line=risk_line(config),
        meta=meta,
    )


def payload_from_benchmark(
    result: BenchmarkResult,
    config: BotConfig,
    start_ms: int,
    end_ms: int,
    data_files: Sequence[Path],
    kind: BenchmarkKind,
    root: Path,
    label: str | None = None,
) -> RunPayload:
    weights = {p.symbol: str(w) for p, w in result.weights.items()}
    meta = build_meta(
        strategy=f"buy_hold_{kind}",
        timeframe=config.strategy.timeframe.value,
        pairs=list(weights),
        start=ms_to_date(start_ms),
        end=ms_to_date(end_ms),
        include_holdout=config.backtest.include_holdout,
        params={"kind": kind, "weights": weights},
        data_files=data_files,
        duration_s=0.0,
        root=root,
    )
    title = "Buy & hold BTC" if kind == "bh_btc" else "Buy & hold equiponderado"
    return RunPayload(
        label=label or f"buy-hold-{kind}",
        title=title,
        strategy_name=f"buy_hold_{kind}",
        spec_path=None,
        params={"kind": kind, "weights": weights},
        config_dump=frozen_config(config, start_ms, end_ms),
        metrics=result.metrics,
        benchmarks={},
        equity=result.equity,
        benchmark_equities={},
        trades=(),
        fills=result.fills,
        events=(),
        data_line=data_line(config, start_ms, end_ms, 0, meta.data_hash),
        costs_line=costs_line(config),
        risk_line="benchmark: sin gestión de riesgo (compra única al inicio del rango)",
        meta=meta,
    )


def register_artifacts(
    build: Callable[[str], RunArtifacts], experiments_dir: Path, kind: str = "EXP"
) -> Path:
    """Toma el siguiente id del tipo y escribe; si otro proceso lo ocupó entre medio, reintenta."""
    last_error: DataError | None = None
    for _attempt in range(5):
        run_id = next_run_id(experiments_dir / "runs", kind)
        try:
            return write_run(experiments_dir, build(run_id))
        except DataError as exc:
            last_error = exc
    msg = f"no se pudo registrar la corrida tras 5 intentos: {last_error}"
    raise DataError(msg)


def register_payload(payload: RunPayload, experiments_dir: Path, kind: str = "EXP") -> Path:
    return register_artifacts(
        lambda run_id: _build_artifacts(payload, run_id, kind), experiments_dir, kind
    )


def _build_artifacts(payload: RunPayload, run_id: str, kind: str) -> RunArtifacts:
    reproducibility = (
        f"git {payload.meta.git_sha}{'*' if payload.meta.git_dirty else ''}, "
        f"params {payload.meta.params_hash}, datos {payload.meta.data_hash}, "
        f"{payload.meta.duration_s:.1f} s en {payload.meta.host}"
    )
    events = Counter(f"{e.kind}:{e.reason}" for e in payload.events)
    report = render_report(
        ReportContext(
            run_id=run_id,
            title=payload.title,
            strategy=payload.strategy_name,
            spec_path=payload.spec_path,
            params=payload.params,
            data_line=payload.data_line,
            costs_line=payload.costs_line,
            risk_line=payload.risk_line,
            reproducibility_line=reproducibility,
            metrics=payload.metrics,
            benchmarks=payload.benchmarks,
            equity=payload.equity,
            trades=payload.trades,
            events=sorted(events.items()),
        )
    )
    png = plot_equity(payload.equity, payload.benchmark_equities, f"{run_id} {payload.title}")
    artifacts = RunArtifacts(
        run_id=run_id,
        kind=kind,
        label=payload.label,
        config=payload.config_dump,
        metrics=payload.metrics.to_dict(),
        benchmarks={k: v.to_dict() for k, v in payload.benchmarks.items()},
        meta=payload.meta,
        report_md=report,
        trades_csv=trades_csv(payload.trades),
        equity_csv=equity_csv(payload.equity, payload.benchmark_equities),
        equity_png=png,
    )
    return artifacts
