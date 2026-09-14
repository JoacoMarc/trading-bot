"""Comandos de validación (ADR-0008): `walkforward` y `optimize`. Registran `WF-` / `OPT-`."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError

from tradingbot.backtest.metrics import Metrics
from tradingbot.cli.backtest_commands import (
    DEFAULT_CONFIG,
    ConfigOption,
    ExperimentsDirOption,
    _fail,
    _load_config,
    _print_comparison,
)
from tradingbot.config.models import ValidationConfig
from tradingbot.config.overrides import deep_merge, parse_set
from tradingbot.config.settings import BotConfig
from tradingbot.domain.errors import TradingBotError
from tradingbot.validation.gates import gate_verdict
from tradingbot.validation.optimizer import OptimizeSettings, run_optimization
from tradingbot.validation.report import register_optimization, register_walkforward
from tradingbot.validation.walkforward import (
    WalkForwardResult,
    WalkForwardSettings,
    run_walkforward,
)

valid_app = typer.Typer(add_completion=False)

SetsOption = Annotated[
    list[str] | None, typer.Option("--set", "-s", help="Override clave.sub=valor (repetible).")
]
PairsOption = Annotated[str | None, typer.Option("--pairs", "-p", help="BTC/USDT,ETH/USDT")]
FromOption = Annotated[str | None, typer.Option("--from", help="Desde (YYYY-MM-DD).")]
ToOption = Annotated[str | None, typer.Option("--to", help="Hasta, exclusivo (YYYY-MM-DD).")]
RegisterOption = Annotated[bool, typer.Option("--register/--no-register")]
LabelOption = Annotated[str | None, typer.Option("--label", help="Sufijo del directorio.")]


def _cli_overrides(pairs: str | None, start: str | None, end: str | None) -> dict[str, Any]:
    cli: dict[str, Any] = {}
    if pairs:
        cli.setdefault("strategy", {})["pairs"] = [p.strip() for p in pairs.split(",") if p.strip()]
    if start:
        cli.setdefault("backtest", {})["start"] = start
    if end:
        cli.setdefault("backtest", {})["end"] = end
    return cli


def _validation_config(cfg: BotConfig, flags: Mapping[str, Any]) -> ValidationConfig:
    """Bloque `validation` de la config pisado por los flags presentes; revalidado por pydantic."""
    provided = {k: v for k, v in flags.items() if v is not None}
    return ValidationConfig.model_validate({**cfg.validation.model_dump(), **provided})


def _every(say: Callable[[str], None], every: int, total: int) -> Callable[[str], None]:
    count = 0

    def emit(message: str) -> None:
        nonlocal count
        count += 1
        if count % every == 0 or count == total:
            say(message)

    return emit


def _print_walkforward(result: WalkForwardResult) -> None:
    typer.echo(
        f"{'#':<3}{'IS':<25}{'OOS':<25}{'retorno':>10}{'sharpe':>8}{'max dd':>9}"
        f"{'trades':>7}  params"
    )
    for w in result.windows:
        m = w.oos_metrics
        sharpe = "-" if m.sharpe is None else f"{m.sharpe:.2f}"
        changed = w.changed_params(result.base_params)
        typer.echo(
            f"{w.window.index + 1:<3}{f'{w.window.is_start} -> {w.window.is_end}':<25}"
            f"{f'{w.window.oos_start} -> {w.window.oos_end}':<25}"
            f"{float(m.total_return) * 100:>+9.2f} %{sharpe:>8}{m.max_drawdown * 100:>8.2f} %"
            f"{m.trades:>7}  {changed if changed else 'base'}"
        )
    columns: dict[str, Metrics | dict[str, Any]] = {"OOS concatenado": result.oos_metrics}
    if result.benchmark_metrics is not None:
        columns["B&H BTC (OOS)"] = result.benchmark_metrics
    if result.full_sample is not None:
        columns["muestra completa"] = result.full_sample.metrics
    _print_comparison(columns)
    mc = result.montecarlo
    typer.echo(
        f"monte carlo ({mc.runs} corridas, {mc.trades} trades): "
        f"max DD p50 {mc.dd_p50 * 100:.2f} %, p95 {mc.dd_p95 * 100:.2f} %, "
        f"p99 {mc.dd_p99 * 100:.2f} %; retorno p05 {mc.return_p05 * 100:+.2f} %"
    )
    if result.plateau is not None and result.plateau.pass_rate is not None:
        typer.echo(
            f"meseta: {len(result.plateau.rows)} variantes, "
            f"pasan {result.plateau.pass_rate * 100:.0f} %"
            + (
                ""
                if result.plateau.relative_pass_rate is None
                else f"; con Sharpe >= 0.5 x base: {result.plateau.relative_pass_rate * 100:.0f} %"
            )
        )
    typer.echo(f"gate 1: {gate_verdict(result.gate)}")
    for check in result.gate:
        typer.echo(f"  {check.mark:<6}{check.name:<32}{check.value:<26}umbral {check.threshold}")
    typer.echo(f"duracion {result.duration_s:.0f} s")


@valid_app.command("walkforward")
def walkforward(
    config: ConfigOption = DEFAULT_CONFIG,
    sets: SetsOption = None,
    pairs: PairsOption = None,
    start: FromOption = None,
    end: ToOption = None,
    is_months: Annotated[int | None, typer.Option("--is-months", min=1)] = None,
    oos_months: Annotated[int | None, typer.Option("--oos-months", min=1)] = None,
    anchored: Annotated[
        bool | None, typer.Option("--anchored/--rolling", help="El IS siempre arranca al inicio.")
    ] = None,
    optimize: Annotated[
        bool | None,
        typer.Option("--optimize/--fixed", help="Optimizar parámetros en cada IS (optuna)."),
    ] = None,
    trials: Annotated[int | None, typer.Option("--trials", help="Trials de optuna.", min=1)] = None,
    seed: Annotated[int | None, typer.Option("--seed", help="Semilla (TPE y Monte Carlo).")] = None,
    objective: Annotated[
        str | None, typer.Option("--objective", help="sharpe | calmar | profit_factor.")
    ] = None,
    min_trades: Annotated[
        int | None, typer.Option("--min-trades", help="Penaliza corridas con menos trades.", min=0)
    ] = None,
    plateau: Annotated[
        bool | None,
        typer.Option("--plateau/--no-plateau", help="Meseta ±20 % sobre la muestra completa."),
    ] = None,
    montecarlo_runs: Annotated[int | None, typer.Option("--montecarlo-runs", min=100)] = None,
    register: RegisterOption = True,
    label: LabelOption = None,
    experiments_dir: ExperimentsDirOption = Path("experiments"),
) -> None:
    """Walk-forward IS/OOS con curva OOS concatenada, Monte Carlo y Gate 1; registra WF-NNNN.

    Los flags pisan el bloque `validation` de la config; el `config.yaml` congelado de un WF-
    trae ese bloque, así que `tradingbot walkforward --config <congelado>` reproduce la corrida.
    """
    flags = {
        "is_months": is_months,
        "oos_months": oos_months,
        "anchored": anchored,
        "optimize": optimize,
        "trials": trials,
        "seed": seed,
        "objective": objective,
        "min_trades": min_trades,
        "plateau": plateau,
        "montecarlo_runs": montecarlo_runs,
    }
    try:
        cfg = _load_config(
            config, deep_merge(parse_set(sets or []), _cli_overrides(pairs, start, end))
        )
        settings = WalkForwardSettings.from_config(_validation_config(cfg, flags))
        result = run_walkforward(cfg, settings, progress=typer.echo)
    except (TradingBotError, ValidationError) as exc:
        _fail(exc)
        return
    _print_walkforward(result)
    if register:
        run_dir = register_walkforward(result, Path.cwd(), experiments_dir, label)
        typer.echo(f"registrado: {run_dir.name} -> {run_dir}")
    else:
        typer.echo("sin registrar (--no-register)")


@valid_app.command("optimize")
def optimize_command(
    config: ConfigOption = DEFAULT_CONFIG,
    sets: SetsOption = None,
    pairs: PairsOption = None,
    start: FromOption = None,
    end: ToOption = None,
    trials: Annotated[int | None, typer.Option("--trials", help="Trials de optuna.", min=1)] = None,
    seed: Annotated[int | None, typer.Option("--seed", help="Semilla del TPE.")] = None,
    objective: Annotated[
        str | None, typer.Option("--objective", help="sharpe | calmar | profit_factor.")
    ] = None,
    min_trades: Annotated[
        int | None, typer.Option("--min-trades", help="Penaliza corridas con menos trades.", min=0)
    ] = None,
    register: RegisterOption = True,
    label: LabelOption = None,
    experiments_dir: ExperimentsDirOption = Path("experiments"),
) -> None:
    """Optimiza con optuna sobre el rango dado (in-sample) y registra OPT-NNNN."""
    flags = {"trials": trials, "seed": seed, "objective": objective, "min_trades": min_trades}
    try:
        cfg = _load_config(
            config, deep_merge(parse_set(sets or []), _cli_overrides(pairs, start, end))
        )
        vcfg = _validation_config(cfg, flags)
        settings = OptimizeSettings(vcfg.trials, vcfg.seed, vcfg.objective, vcfg.min_trades)
        run = run_optimization(cfg, settings, progress=_every(typer.echo, 10, vcfg.trials))
    except (TradingBotError, ValidationError) as exc:
        _fail(exc)
        return
    res = run.result
    typer.echo(
        f"mejor score {res.best_score:.3f} ({res.completed}/{settings.trials} trials validos): "
        f"{res.best_params}"
    )
    columns: dict[str, Metrics | dict[str, Any]] = {"mejor IS": run.best_run.metrics}
    for name, bench in run.best_run.benchmarks.items():
        columns[name] = bench.metrics
    _print_comparison(columns)
    typer.echo("advertencia: metricas in-sample; la evidencia es la curva OOS del walk-forward")
    if register:
        run_dir = register_optimization(run, Path.cwd(), experiments_dir, label)
        typer.echo(f"registrado: {run_dir.name} -> {run_dir}")
    else:
        typer.echo("sin registrar (--no-register)")
