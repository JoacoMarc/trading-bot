"""Comandos de backtesting y registro: `backtest`, `benchmark`, `experiments ...`."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError

from tradingbot.backtest.metrics import Metrics
from tradingbot.backtest.runner import (
    BacktestRun,
    BenchmarkKind,
    payload_from_backtest,
    payload_from_benchmark,
    register_payload,
    run_backtest,
    run_benchmark,
)
from tradingbot.config.overrides import deep_merge, parse_set
from tradingbot.config.settings import BotConfig
from tradingbot.domain.errors import TradingBotError
from tradingbot.persistence.experiments import RunSummary, load_runs, sync_registry

bt_app = typer.Typer(add_completion=False)
experiments_app = typer.Typer(
    add_completion=False,
    help="Corridas registradas en experiments/runs (list, show, compare, sync).",
    no_args_is_help=True,
)

DEFAULT_CONFIG = Path("configs") / "backtest.yaml"
ConfigOption = Annotated[
    Path, typer.Option("--config", "-c", help="YAML de configuración (modo backtest).")
]
ExperimentsDirOption = Annotated[
    Path, typer.Option("--experiments-dir", help="Raíz del registro (default: experiments).")
]


def _fail(exc: Exception) -> None:
    typer.echo(f"error: {exc}", err=True)
    raise typer.Exit(code=1)


def _load_config(config: Path, overrides: Mapping[str, Any]) -> BotConfig:
    if not config.exists():
        msg = f"no existe {config}; copiar configs/backtest.example.yaml a {config}"
        raise TradingBotError(msg)
    return BotConfig.load(config, overrides=overrides)


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:+.2f} %"
    except (TypeError, ValueError):
        return "-"


def _num(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def _summary_rows(metrics: Metrics | Mapping[str, Any]) -> dict[str, str]:
    data = metrics.to_dict() if isinstance(metrics, Metrics) else dict(metrics)
    return {
        "retorno": _pct(data.get("total_return")),
        "cagr": _pct(data.get("cagr")),
        "sharpe": _num(data.get("sharpe")),
        "max dd": _pct(data.get("max_drawdown")),
        "pf": _num(data.get("profit_factor")),
        "trades": str(data.get("trades", "-")),
        "exposicion": _pct(data.get("exposure")),
    }


def _print_comparison(columns: Mapping[str, Metrics | Mapping[str, Any]]) -> None:
    names = list(columns)
    rows = {name: _summary_rows(m) for name, m in columns.items()}
    width = max(12, *(len(n) for n in names))
    typer.echo(f"{'metrica':<12}" + "".join(f"{n[:width]:>{width + 2}}" for n in names))
    for key in ("retorno", "cagr", "sharpe", "max dd", "pf", "trades", "exposicion"):
        typer.echo(f"{key:<12}" + "".join(f"{rows[n][key]:>{width + 2}}" for n in names))


def _print_backtest(run: BacktestRun) -> None:
    columns: dict[str, Metrics | Mapping[str, Any]] = {run.strategy.name: run.metrics}
    for name, bench in run.benchmarks.items():
        columns[name] = bench.metrics
    _print_comparison(columns)
    stats = run.engine_result.stats
    typer.echo(
        f"velas {stats.bars}, fills {stats.fills}, senales {dict(stats.signals)}, "
        f"rechazos {dict(stats.rejections)}, stuck {sorted(p.symbol for p in stats.stuck_pairs)}"
    )
    typer.echo(f"duracion {run.duration_s:.1f} s")


@bt_app.command("backtest")
def backtest(
    config: ConfigOption = DEFAULT_CONFIG,
    strategy: Annotated[str | None, typer.Option("--strategy", help="Nombre registrado.")] = None,
    pairs: Annotated[str | None, typer.Option("--pairs", "-p", help="BTC/USDT,ETH/USDT")] = None,
    start: Annotated[str | None, typer.Option("--from", help="Desde (YYYY-MM-DD).")] = None,
    end: Annotated[str | None, typer.Option("--to", help="Hasta, exclusivo (YYYY-MM-DD).")] = None,
    sets: Annotated[
        list[str] | None, typer.Option("--set", "-s", help="Override clave.sub=valor (repetible).")
    ] = None,
    include_holdout: Annotated[
        bool, typer.Option("--include-holdout", help="Solo en la corrida final de una familia.")
    ] = False,
    register: Annotated[
        bool, typer.Option("--register/--no-register", help="Registrar en experiments/.")
    ] = True,
    label: Annotated[str | None, typer.Option("--label", help="Sufijo del directorio.")] = None,
    experiments_dir: ExperimentsDirOption = Path("experiments"),
) -> None:
    """Corre un backtest con el mismo Engine de paper/live y lo registra en experiments/."""
    overrides: dict[str, Any] = parse_set(sets or [])
    cli: dict[str, Any] = {}
    if strategy:
        cli.setdefault("strategy", {})["name"] = strategy
    if pairs:
        cli.setdefault("strategy", {})["pairs"] = [p.strip() for p in pairs.split(",") if p.strip()]
    if start:
        cli.setdefault("backtest", {})["start"] = start
    if end:
        cli.setdefault("backtest", {})["end"] = end
    if include_holdout:
        cli.setdefault("backtest", {})["include_holdout"] = True
    try:
        cfg = _load_config(config, deep_merge(overrides, cli))
        run = run_backtest(cfg)
    except (TradingBotError, ValidationError) as exc:
        _fail(exc)
        return
    _print_backtest(run)
    if register:
        payload = payload_from_backtest(run, Path.cwd(), label)
        run_dir = register_payload(payload, experiments_dir, kind="EXP")
        typer.echo(f"registrado: {run_dir.name} -> {run_dir}")
    else:
        typer.echo("sin registrar (--no-register)")


@bt_app.command("benchmark")
def benchmark(
    config: ConfigOption = DEFAULT_CONFIG,
    kind: Annotated[
        str, typer.Option("--kind", "-k", help="bh_btc (buy & hold BTC) o equal_weight.")
    ] = "bh_btc",
    label: Annotated[str | None, typer.Option("--label")] = None,
    register: Annotated[bool, typer.Option("--register/--no-register")] = True,
    experiments_dir: ExperimentsDirOption = Path("experiments"),
) -> None:
    """Buy & hold sobre el mismo rango y costos que el backtest, registrado como EXP."""
    if kind not in ("bh_btc", "equal_weight"):
        _fail(TradingBotError(f"kind desconocido {kind!r}; usar bh_btc o equal_weight"))
        return
    bench_kind: BenchmarkKind = "bh_btc" if kind == "bh_btc" else "equal_weight"
    try:
        cfg = _load_config(config, {})
        result, cfg, start_ms, end_ms, files = run_benchmark(cfg, bench_kind)
    except (TradingBotError, ValidationError) as exc:
        _fail(exc)
        return
    _print_comparison({result.name: result.metrics})
    if register:
        payload = payload_from_benchmark(
            result, cfg, start_ms, end_ms, files, bench_kind, Path.cwd(), label
        )
        run_dir = register_payload(payload, experiments_dir, kind="EXP")
        typer.echo(f"registrado: {run_dir.name} -> {run_dir}")


def _find(summaries: list[RunSummary], run_id: str) -> RunSummary:
    for summary in summaries:
        if summary.run_id == run_id or summary.path.name == run_id:
            return summary
    msg = f"no existe la corrida {run_id!r}"
    raise TradingBotError(msg)


@experiments_app.command("list")
def experiments_list(experiments_dir: ExperimentsDirOption = Path("experiments")) -> None:
    """Lista las corridas registradas con sus métricas principales."""
    summaries = load_runs(experiments_dir)
    if not summaries:
        typer.echo(f"sin corridas en {experiments_dir / 'runs'}")
        return
    header = (
        f"{'id':<10} {'fecha':<10} {'estrategia':<16} {'retorno':>9} {'sharpe':>7} "
        f"{'max dd':>9} {'trades':>6}  veredicto"
    )
    typer.echo(header)
    for s in summaries:
        m = s.metrics
        created = str(s.meta.get("created_at", ""))[:10]
        strategy_name = str(s.meta.get("strategy", ""))[:16]
        typer.echo(
            f"{s.run_id:<10} {created:<10} {strategy_name:<16} {_pct(m.get('total_return')):>9} "
            f"{_num(m.get('sharpe')):>7} {_pct(m.get('max_drawdown')):>9} "
            f"{m.get('trades', '-')!s:>6}  {s.verdict}"
        )


@experiments_app.command("show")
def experiments_show(
    run_id: Annotated[str, typer.Argument(help="EXP-0003 o el nombre del directorio.")],
    experiments_dir: ExperimentsDirOption = Path("experiments"),
) -> None:
    """Muestra métricas, benchmarks, metadatos y veredicto de una corrida."""
    try:
        summary = _find(load_runs(experiments_dir), run_id)
    except (TradingBotError, ValidationError) as exc:
        _fail(exc)
        return
    typer.echo(f"{summary.run_id} [{summary.kind}] {summary.label}  ->  {summary.path}")
    typer.echo(f"veredicto: {summary.verdict}")
    columns: dict[str, Metrics | Mapping[str, Any]] = {
        "corrida": summary.metrics,
        **summary.benchmarks,
    }
    _print_comparison(columns)
    meta = {k: v for k, v in summary.meta.items() if k != "extra"}
    typer.echo("meta: " + json.dumps(meta, ensure_ascii=False, default=str))
    extra = summary.meta.get("extra") or {}
    if extra:
        typer.echo("extra: " + ", ".join(sorted(extra)) + " (detalle en metrics.json)")


@experiments_app.command("compare")
def experiments_compare(
    run_ids: Annotated[list[str], typer.Argument(help="Dos o más ids.")],
    experiments_dir: ExperimentsDirOption = Path("experiments"),
) -> None:
    """Compara métricas de varias corridas lado a lado."""
    summaries = load_runs(experiments_dir)
    try:
        chosen = [_find(summaries, rid) for rid in run_ids]
    except (TradingBotError, ValidationError) as exc:
        _fail(exc)
        return
    _print_comparison({s.run_id: s.metrics for s in chosen})
    for s in chosen:
        typer.echo(
            f"{s.run_id}: {s.meta.get('strategy')} params {s.meta.get('params_hash')} "
            f"-> {s.verdict}"
        )


@experiments_app.command("sync")
def experiments_sync(experiments_dir: ExperimentsDirOption = Path("experiments")) -> None:
    """Regenera REGISTRY.md desde runs/*/metrics.json y los veredictos de cada REPORT.md."""
    path = sync_registry(experiments_dir)
    typer.echo(f"{path} regenerado con {len(load_runs(experiments_dir))} corridas")
