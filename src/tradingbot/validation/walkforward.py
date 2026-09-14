"""Walk-forward (ADR-0008): ventanas IS/OOS, curva OOS concatenada y Gate 1.

Modo `fijo`: los mismos parámetros en todas las ventanas (robustez temporal de una config).
Modo `optimizado`: optuna elige los parámetros sobre cada IS y se evalúan una vez en su OOS.
La evidencia es siempre la curva OOS concatenada; el IS nunca se reporta como resultado.
"""

from __future__ import annotations

import calendar
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from tradingbot.backtest.benchmark import BenchmarkResult
from tradingbot.backtest.metrics import EquityPoint, Metrics, compute_metrics
from tradingbot.backtest.runner import (
    BacktestRun,
    date_to_ms,
    derive_config,
    load_candles,
    load_markets_for,
    resolve_range,
    run_backtest,
)
from tradingbot.config.models import ValidationConfig
from tradingbot.config.settings import BotConfig
from tradingbot.data.store import ParquetStore
from tradingbot.domain.candle import Candle
from tradingbot.domain.errors import ConfigError
from tradingbot.domain.orders import Fill
from tradingbot.domain.pair import Pair
from tradingbot.domain.positions import Trade
from tradingbot.exchange.binance import MarketInfo
from tradingbot.strategy.registry import build_strategy, effective_warmup
from tradingbot.validation.gates import GateCheck, GateThresholds, evaluate_gate1
from tradingbot.validation.montecarlo import (
    MonteCarloResult,
    block_bootstrap_daily,
    bootstrap_trades,
)
from tradingbot.validation.optimizer import OptimizationResult, OptimizeSettings, optimize
from tradingbot.validation.plateau import PlateauResult, run_plateau
from tradingbot.validation.regimes import RegimeCheck, YearRegime, check_regimes, yearly_regimes

Mode = Literal["fijo", "optimizado"]
Progress = Callable[[str], None]


def add_months(value: date, months: int) -> date:
    """Suma meses de calendario; el día se acota al último del mes destino."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def ms_to_day(ts_ms: int) -> date:
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).date()


@dataclass(frozen=True, slots=True)
class Window:
    index: int
    is_start: date
    is_end: date
    oos_start: date
    oos_end: date

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "is": [self.is_start.isoformat(), self.is_end.isoformat()],
            "oos": [self.oos_start.isoformat(), self.oos_end.isoformat()],
        }


def build_windows(
    start: date, end: date, *, is_months: int = 24, oos_months: int = 6, anchored: bool = False
) -> list[Window]:
    """Ventanas completas dentro de `[start, end)`; el paso es igual al OOS (tramos contiguos)."""
    if is_months <= 0 or oos_months <= 0:
        msg = f"is_months y oos_months deben ser positivos ({is_months}, {oos_months})"
        raise ConfigError(msg)
    windows: list[Window] = []
    index = 0
    while True:
        is_start = start if anchored else add_months(start, index * oos_months)
        is_end = add_months(start, is_months + index * oos_months)
        oos_end = add_months(is_end, oos_months)
        if oos_end > end:
            break
        windows.append(Window(index, is_start, is_end, is_end, oos_end))
        index += 1
    if not windows:
        msg = (
            f"el rango {start} -> {end} no alcanza para IS {is_months} m + OOS {oos_months} m; "
            "achicar las ventanas o ampliar los datos"
        )
        raise ConfigError(msg)
    return windows


@dataclass(frozen=True, slots=True)
class WalkForwardSettings:
    is_months: int = 24
    oos_months: int = 6
    anchored: bool = False
    optimize: OptimizeSettings | None = None
    plateau: bool = False
    montecarlo_runs: int = 5_000
    seed: int = 42
    thresholds: GateThresholds = field(default_factory=GateThresholds)

    @property
    def mode(self) -> Mode:
        return "optimizado" if self.optimize is not None else "fijo"

    @classmethod
    def from_config(cls, cfg: ValidationConfig) -> WalkForwardSettings:
        return cls(
            is_months=cfg.is_months,
            oos_months=cfg.oos_months,
            anchored=cfg.anchored,
            optimize=OptimizeSettings(cfg.trials, cfg.seed, cfg.objective, cfg.min_trades)
            if cfg.optimize
            else None,
            plateau=cfg.plateau,
            montecarlo_runs=cfg.montecarlo_runs,
            seed=cfg.seed,
            thresholds=GateThresholds(
                trades_full_min=cfg.trades_full_min, trades_oos_min=cfg.trades_oos_min
            ),
        )

    def to_config_dict(self) -> dict[str, Any]:
        """Bloque `validation` del `config.yaml` congelado: recargarlo reproduce la corrida."""
        opt = self.optimize
        defaults = ValidationConfig()
        return {
            "is_months": self.is_months,
            "oos_months": self.oos_months,
            "anchored": self.anchored,
            "optimize": opt is not None,
            "trials": opt.trials if opt else defaults.trials,
            "seed": self.seed,
            "objective": opt.objective if opt else defaults.objective,
            "min_trades": opt.min_trades if opt else defaults.min_trades,
            "plateau": self.plateau,
            "montecarlo_runs": self.montecarlo_runs,
            "trades_full_min": self.thresholds.trades_full_min,
            "trades_oos_min": self.thresholds.trades_oos_min,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_months": self.is_months,
            "oos_months": self.oos_months,
            "anchored": self.anchored,
            "mode": self.mode,
            "optimize": None if self.optimize is None else self.optimize.to_dict(),
            "plateau": self.plateau,
            "montecarlo_runs": self.montecarlo_runs,
            "seed": self.seed,
        }


@dataclass(frozen=True, slots=True)
class WindowResult:
    window: Window
    params: dict[str, Any]
    optimization: OptimizationResult | None
    run: BacktestRun  # corrida OOS
    benchmark: BenchmarkResult | None  # B&H BTC del tramo OOS

    @property
    def oos_metrics(self) -> Metrics:
        return self.run.metrics

    @property
    def invested(self) -> list[bool]:
        return [len(s.positions) > 0 for s in self.run.engine_result.store.snapshots()]

    @property
    def optimization_failed(self) -> bool:
        return self.optimization is not None and not self.optimization.best_params

    @property
    def open_at_end(self) -> int:
        """Posiciones que siguen abiertas al cierre del tramo: la equity las marca, `trades` no."""
        snapshot = self.run.engine_result.final_snapshot
        return 0 if snapshot is None else len(snapshot.positions)

    @property
    def unrealized_pnl(self) -> Decimal:
        """PnL bruto (sin fee de salida) de las posiciones abiertas al cierre del tramo."""
        snapshot = self.run.engine_result.final_snapshot
        if snapshot is None:
            return Decimal(0)
        return sum(
            (
                (snapshot.marks[p.pair] - p.entry_price) * p.qty
                for p in snapshot.positions
                if p.pair in snapshot.marks
            ),
            Decimal(0),
        )

    @property
    def rejections(self) -> dict[str, int]:
        """Rechazos del RiskManager en el tramo OOS por motivo (slots, protecciones...)."""
        return dict(self.run.engine_result.stats.rejections)

    def changed_params(self, base: Mapping[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in self.params.items() if base.get(k) != v}


@dataclass(frozen=True, slots=True)
class WalkForwardResult:
    config: BotConfig
    settings: WalkForwardSettings
    base_params: dict[str, Any]
    windows: list[WindowResult]
    oos_equity: list[EquityPoint]
    oos_invested: list[bool]
    oos_trades: list[Trade]
    oos_fills: list[Fill]
    oos_metrics: Metrics
    benchmark_equity: list[EquityPoint]
    benchmark_metrics: Metrics | None
    extra_benchmarks: dict[str, tuple[list[EquityPoint], Metrics]]  # otros B&H encadenados
    full_sample: BacktestRun | None
    regimes: list[YearRegime]
    regimes_source: str
    montecarlo: MonteCarloResult
    montecarlo_daily: MonteCarloResult  # bootstrap por bloques de retornos diarios (informativo)
    plateau: PlateauResult | None
    gate: list[GateCheck]
    unused_tail: tuple[date, date] | None
    inactive_pairs: list[Pair]
    data_files: list[Path]
    start_ms: int
    end_ms: int
    duration_s: float

    @property
    def mode(self) -> Mode:
        return self.settings.mode

    @property
    def window_returns(self) -> list[Decimal]:
        return [w.oos_metrics.total_return for w in self.windows]

    @property
    def strategy_name(self) -> str:
        return self.windows[0].run.strategy.name


def chain_equity(segments: Sequence[Sequence[EquityPoint]], initial: Decimal) -> list[EquityPoint]:
    """Encadena tramos: cada uno se re-escala para arrancar donde terminó el anterior."""
    out: list[EquityPoint] = []
    level = initial
    for segment in segments:
        if not segment:
            continue
        base = segment[0][1]
        if base <= 0:
            msg = "un tramo de equity arranca en cero o negativo; no se puede encadenar"
            raise ValueError(msg)
        factor = level / base
        for ts, value in segment:
            if out and ts <= out[-1][0]:
                continue  # tramos contiguos: el primer punto puede coincidir con el último anterior
            out.append((ts, value * factor))
        level = out[-1][1] if out else level
    return out


BENCHMARK_NAME = "B&H BTC"


def _benchmark_of(run: BacktestRun) -> BenchmarkResult | None:
    """Solo B&H BTC: un universo sin BTC queda sin benchmark y el gate lo marca n/a."""
    return run.benchmarks.get(BENCHMARK_NAME)


def _align_up_to_day(ts_ms: int) -> date:
    day = ms_to_day(ts_ms)
    return day if date_to_ms(day) == ts_ms else day + timedelta(days=1)


def _throttled(say: Progress, every: int, total: int) -> Progress:
    count = 0

    def emit(message: str) -> None:
        nonlocal count
        count += 1
        if count % every == 0 or count == total:
            say(f"  {message}")

    return emit


def run_walkforward(
    config: BotConfig,
    settings: WalkForwardSettings,
    *,
    markets: Mapping[Pair, MarketInfo] | None = None,
    candles: Mapping[Pair, Sequence[Candle]] | None = None,
    progress: Progress | None = None,
) -> WalkForwardResult:
    started = time.perf_counter()
    say: Progress = progress or (lambda _message: None)
    if config.backtest.include_holdout:
        msg = "el walk-forward nunca incluye el holdout (docs/GATES.md)"
        raise ConfigError(msg)
    strategy = build_strategy(config.strategy)
    warmup = effective_warmup(config.strategy, strategy)
    store = ParquetStore(config.data.data_dir)
    start_ms, end_ms = resolve_range(config, store, warmup)
    cached = candles if candles is not None else load_candles(config, end_ms)
    market_infos = load_markets_for(list(config.strategy.pairs), markets)
    windows = build_windows(
        _align_up_to_day(start_ms),
        ms_to_day(end_ms),
        is_months=settings.is_months,
        oos_months=settings.oos_months,
        anchored=settings.anchored,
    )
    base_params: dict[str, Any] = strategy.params.model_dump(mode="json")
    space = strategy.search_space()

    def backtest_metrics(cfg: BotConfig, params: Mapping[str, Any]) -> Metrics:
        return run_backtest(
            derive_config(cfg, params=params),
            markets=market_infos,
            with_benchmarks=False,
            candles=cached,
        ).metrics

    results: list[WindowResult] = []
    total = len(windows)
    for window in windows:
        params = dict(base_params)
        optimization: OptimizationResult | None = None
        if settings.optimize is not None:
            say(
                f"ventana {window.index + 1}/{total}: optimizando IS {window.is_start} -> "
                f"{window.is_end} ({settings.optimize.trials} trials)"
            )
            cfg_is = derive_config(config, start=window.is_start, end=window.is_end)

            def run_is(p: Mapping[str, Any], cfg: BotConfig = cfg_is) -> Metrics:
                return backtest_metrics(cfg, p)

            optimization = optimize(
                run_is,
                space,
                settings.optimize,
                progress=_throttled(say, 10, settings.optimize.trials),
            )
            params.update(optimization.best_params)
            if not optimization.best_params:
                say(f"ventana {window.index + 1}/{total}: optimización fallida, corre con la base")
        cfg_oos = derive_config(config, params=params, start=window.oos_start, end=window.oos_end)
        run = run_backtest(cfg_oos, markets=market_infos, with_benchmarks=True, candles=cached)
        results.append(WindowResult(window, params, optimization, run, _benchmark_of(run)))
        say(
            f"ventana {window.index + 1}/{total}: OOS {window.oos_start} -> {window.oos_end}: "
            f"retorno {run.metrics.total_return * 100:+.2f} %, {run.metrics.trades} trades"
        )

    initial = config.backtest.initial_cash
    oos_equity = chain_equity([r.run.equity for r in results], initial)
    oos_invested = [flag for r in results for flag in r.invested]
    oos_trades = [t for r in results for t in r.run.trades]
    oos_fills = [f for r in results for f in r.run.fills]
    oos_metrics = compute_metrics(oos_equity, oos_invested, oos_trades, oos_fills)

    bench_segments = [r.benchmark.equity for r in results if r.benchmark is not None]
    benchmark_equity = (
        chain_equity(bench_segments, initial) if len(bench_segments) == len(results) else []
    )
    benchmark_metrics = (
        compute_metrics(benchmark_equity, [True] * len(benchmark_equity), [], [])
        if benchmark_equity
        else None
    )
    # Otros benchmarks presentes en todas las ventanas (equiponderado, B&H BTC filtrado).
    common = set.intersection(*(set(r.run.benchmarks) for r in results)) - {BENCHMARK_NAME}
    extra_benchmarks: dict[str, tuple[list[EquityPoint], Metrics]] = {}
    for name in sorted(common):
        chained = chain_equity([r.run.benchmarks[name].equity for r in results], initial)
        extra_benchmarks[name] = (chained, compute_metrics(chained, [True] * len(chained), [], []))

    full_sample: BacktestRun | None = None
    plateau: PlateauResult | None = None
    if settings.optimize is None:
        cfg_full = derive_config(config, start=windows[0].is_start, end=windows[-1].oos_end)
        say(f"muestra completa {windows[0].is_start} -> {windows[-1].oos_end} con parámetros fijos")
        full_sample = run_backtest(
            cfg_full, markets=market_infos, with_benchmarks=False, candles=cached
        )
        regimes = yearly_regimes(full_sample.equity, list(full_sample.trades))
        regimes_source = "muestra completa, parámetros fijos"
        regime_checks = check_regimes(regimes)
        if settings.plateau:

            def run_full(p: Mapping[str, Any]) -> Metrics:
                return backtest_metrics(cfg_full, p)

            plateau = run_plateau(
                base_params, space, run_full, progress=say, base_metrics=full_sample.metrics
            )
    else:
        regimes = yearly_regimes(oos_equity, oos_trades)
        regimes_source = "curva OOS concatenada (informativo: n/a en modo optimizado)"
        # ADR-0008: en modo optimizado los regímenes por año no se evalúan, solo se informan.
        regime_checks = [
            RegimeCheck(c.label, c.threshold, c.value, None) for c in check_regimes(regimes)
        ]

    inactive = sorted({p for r in results for p in r.run.inactive})
    montecarlo = bootstrap_trades(
        [t.pnl for t in oos_trades], initial, runs=settings.montecarlo_runs, seed=settings.seed
    )
    montecarlo_daily = block_bootstrap_daily(
        oos_equity, runs=settings.montecarlo_runs, seed=settings.seed
    )
    gate = evaluate_gate1(
        oos=oos_metrics,
        benchmark=benchmark_metrics,
        window_returns=[r.oos_metrics.total_return for r in results],
        full_sample_trades=None if full_sample is None else full_sample.metrics.trades,
        regimes=regime_checks,
        regimes_source=regimes_source,
        plateau_pass_rate=None if plateau is None else plateau.pass_rate,
        montecarlo_dd_p95=montecarlo.dd_p95 if oos_trades else None,
        thresholds=settings.thresholds,
        inactive_pairs=[p.symbol for p in inactive],
        universe=len(config.strategy.pairs),
    )
    range_end = ms_to_day(end_ms)
    unused = (windows[-1].oos_end, range_end) if windows[-1].oos_end < range_end else None
    return WalkForwardResult(
        config=config,
        settings=settings,
        base_params=base_params,
        windows=results,
        oos_equity=oos_equity,
        oos_invested=oos_invested,
        oos_trades=oos_trades,
        oos_fills=oos_fills,
        oos_metrics=oos_metrics,
        benchmark_equity=benchmark_equity,
        benchmark_metrics=benchmark_metrics,
        extra_benchmarks=extra_benchmarks,
        full_sample=full_sample,
        regimes=regimes,
        regimes_source=regimes_source,
        montecarlo=montecarlo,
        montecarlo_daily=montecarlo_daily,
        plateau=plateau,
        gate=gate,
        unused_tail=unused,
        inactive_pairs=inactive,
        data_files=list(results[0].run.data_files),
        start_ms=start_ms,
        end_ms=end_ms,
        duration_s=time.perf_counter() - started,
    )
