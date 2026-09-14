"""Artefactos de `WF-` y `OPT-` (ADR-0006 / ADR-0008): REPORT.md, metrics.json, CSV y PNG."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from tradingbot.backtest.report import equity_csv, metrics_table, plot_equity, trades_csv
from tradingbot.backtest.runner import (
    costs_line,
    data_line,
    date_to_ms,
    frozen_config,
    ms_to_date,
    register_artifacts,
    risk_line,
    spec_path,
)
from tradingbot.persistence.experiments import ExperimentMeta, RunArtifacts, build_meta
from tradingbot.validation.gates import GateCheck, gate_verdict
from tradingbot.validation.optimizer import OptimizationResult, OptimizationRun
from tradingbot.validation.regimes import YearRegime
from tradingbot.validation.walkforward import WalkForwardResult

BENCH_OOS = "B&H BTC (OOS)"


def _pct(value: Decimal | float | None) -> str:
    return "-" if value is None else f"{float(value) * 100:+.2f} %"


def _num(value: float | Decimal | None, digits: int = 2) -> str:
    return "-" if value is None else f"{float(value):.{digits}f}"


def _money(value: Decimal) -> str:
    return f"{value:,.2f}"


def _params_table(params: Mapping[str, Any]) -> str:
    rows = "\n".join(f"| `{k}` | `{v}` |" for k, v in sorted(params.items()))
    return f"| Parámetro | Valor |\n|---|---|\n{rows}"


def _changes(changed: Mapping[str, Any]) -> str:
    return "base" if not changed else ", ".join(f"{k}={v}" for k, v in sorted(changed.items()))


def gate_table(checks: Sequence[GateCheck]) -> str:
    rows = "\n".join(
        f"| {c.name} | {c.threshold} | {c.value} | {c.mark} | {c.note} |" for c in checks
    )
    return f"| Criterio | Umbral | Valor | Resultado | Nota |\n|---|---|---|---|---|\n{rows}"


def regimes_table(rows: Sequence[YearRegime]) -> str:
    body = (
        "\n".join(
            f"| {r.year}{'' if r.complete else ' (parcial)'} | {_pct(r.total_return)} | "
            f"{_pct_abs(r.max_drawdown)} | {r.trades} | {_money(r.pnl)} |"
            for r in rows
        )
        or "| — | — | — | — | — |"
    )
    return f"| Año | Retorno | Max DD intra-año | Trades | PnL |\n|---|---|---|---|---|\n{body}"


def _reproducibility(meta: ExperimentMeta) -> str:
    return (
        f"git {meta.git_sha}{'*' if meta.git_dirty else ''}, params {meta.params_hash}, "
        f"datos {meta.data_hash}, {meta.duration_s:.1f} s en {meta.host}"
    )


# ----------------------------------------------------------------------------- walk-forward


def _pct_abs(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.2f} %"


def render_walkforward_report(
    result: WalkForwardResult, run_id: str, meta: ExperimentMeta, root: Path
) -> str:
    cfg = result.config
    s = result.settings
    title = (
        f"{run_id} — {result.strategy_name} {cfg.strategy.timeframe.value} walk-forward "
        f"IS {s.is_months} m / OOS {s.oos_months} m ({result.mode})"
    )
    opt = s.optimize
    mode_line = (
        "modo fijo (mismos parámetros en todas las ventanas)"
        if opt is None
        else (
            f"modo optimizado: optuna TPE, {opt.trials} trials por ventana, semilla {opt.seed}, "
            f"objetivo `{opt.objective}`, min_trades {opt.min_trades}"
        )
    )
    unused = (
        ""
        if result.unused_tail is None
        else f"; sin usar {result.unused_tail[0]} -> {result.unused_tail[1]}"
    )
    window_rows = "\n".join(
        f"| {w.window.index + 1} | {w.window.is_start} -> {w.window.is_end} | "
        f"{w.window.oos_start} -> {w.window.oos_end} | "
        f"{'optimización fallida: base' if w.optimization_failed else _changes(w.changed_params(result.base_params))} | "
        f"{_pct(w.oos_metrics.total_return)} | {_num(w.oos_metrics.sharpe)} | "
        f"{_pct_abs(w.oos_metrics.max_drawdown)} | {w.oos_metrics.trades} | {_num(w.oos_metrics.profit_factor)} | "
        f"{w.open_at_end}{'' if w.open_at_end == 0 else f' ({w.unrealized_pnl:+,.2f})'} | "
        f"{w.rejections.get('max_positions', 0)} |"
        for w in result.windows
    )
    open_total = sum(w.open_at_end for w in result.windows)
    open_note = (
        ""
        if open_total == 0
        else (
            f"\n{open_total} posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a "
            "mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).\n"
        )
    )
    inactive_note = (
        ""
        if not result.inactive_pairs
        else (
            "\nPares sin velas suficientes en alguna ventana: "
            + ", ".join(p.symbol for p in result.inactive_pairs)
            + ".\n"
        )
    )
    activation = (
        result.full_sample.activation
        if result.full_sample is not None
        else {p: t for w in result.windows for p, t in w.run.activation.items()}
    )
    benchmarks = {BENCH_OOS: result.benchmark_metrics} if result.benchmark_metrics else {}
    benchmarks.update({f"{n} (OOS)": m for n, (_e, m) in result.extra_benchmarks.items()})
    oos = result.oos_metrics
    mc = result.montecarlo
    mcd = result.montecarlo_daily
    plateau_section = ""
    if result.plateau is not None:
        rows = sorted(result.plateau.rows, key=lambda r: (r.passed, r.total_return or Decimal(0)))
        worst = "\n".join(
            f"| {_changes({k: v for k, v in r.params.items() if result.base_params.get(k) != v})} | "
            f"{_pct(r.total_return)} | {_num(r.profit_factor)} | {_num(r.sharpe)} | {'-' if r.trades is None else r.trades} | "
            f"{'sí' if r.passed else 'no'} |"
            for r in rows[:8]
        )
        plateau_section = (
            f"## Meseta ±{result.plateau.pct * 100:.0f} %\n\n"
            f"{len(result.plateau.rows)} variantes, pasan {_pct(result.plateau.pass_rate)} "
            "(PF > 1.1 y retorno > 0). "
            + (
                ""
                if result.plateau.relative_pass_rate is None
                else (
                    f"Informativo: {_pct(result.plateau.relative_pass_rate)} de las variantes tiene "
                    f"Sharpe >= 0.5 x el base ({_num(result.plateau.base_sharpe)}). "
                )
            )
            + "Las 8 peores:\n\n"
            + "".join(f"> Aviso: {w}\n\n" for w in result.plateau.warnings)
            + f"| Cambios | Retorno | PF | Sharpe | Trades | Pasa |\n|---|---|---|---|---|---|\n{worst}\n\n"
        )
    full_line = ""
    if result.full_sample is not None:
        fm = result.full_sample.metrics
        full_line = (
            f"\nMuestra completa con parámetros fijos ({ms_to_date(result.full_sample.start_ms)} -> "
            f"{ms_to_date(result.full_sample.end_ms)}): retorno {_pct(fm.total_return)}, Sharpe {_num(fm.sharpe)}, "
            f"max DD {_pct(fm.max_drawdown)}, {fm.trades} trades.\n"
        )
    return f"""# {title}

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `{result.strategy_name}` · spec: `{spec_path(result.strategy_name, root) or "—"}`
- Datos: {data_line(cfg, result.start_ms, result.end_ms, result.windows[0].run.warmup, meta.data_hash, activation, result.inactive_pairs)}
- Costos: {costs_line(cfg)}
- Riesgo: {risk_line(cfg)}
- Walk-forward: IS {s.is_months} m / OOS {s.oos_months} m, {"anclado" if s.anchored else "rodante"}, {len(result.windows)} ventanas{unused}; {mode_line}
- Reproducibilidad: {_reproducibility(meta)}

{_params_table(result.base_params)}

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
{window_rows}
{open_note}{inactive_note}
## Curva OOS concatenada

{metrics_table(oos, benchmarks)}

Rango OOS {result.windows[0].window.oos_start} -> {result.windows[-1].window.oos_end}. Equity encadenada {_money(oos.initial_equity)} -> {_money(oos.final_equity)} USDT.
{full_line}
## Gate 1 — backtest -> paper: {gate_verdict(result.gate)}

{gate_table(result.gate)}

## Regímenes por año ({result.regimes_source})

{regimes_table(result.regimes)}

## Monte Carlo (bootstrap de trades OOS)

{mc.runs:,} corridas sobre {mc.trades} trades, semilla {mc.seed}: max DD p50 {_pct(mc.dd_p50)}, p95 {_pct(mc.dd_p95)}, p99 {_pct(mc.dd_p99)}; retorno p05 {_pct(mc.return_p05)}, p50 {_pct(mc.return_p50)}.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los {mcd.trades} retornos diarios OOS: max DD p50 {_pct(mcd.dd_p50)}, p95 {_pct(mcd.dd_p95)}, p99 {_pct(mcd.dd_p99)}; retorno p05 {_pct(mcd.return_p05)}, p50 {_pct(mcd.return_p50)}.

{plateau_section}## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: pendiente
- **Por qué**:
- **Qué se aprendió**:
- **Siguiente experimento propuesto**:
"""


def walkforward_meta(result: WalkForwardResult, root: Path) -> ExperimentMeta:
    cfg = result.config
    windows_extra = [
        {
            **w.window.to_dict(),
            "params": w.changed_params(result.base_params),
            "is_score": None if w.optimization is None else w.optimization.best_score,
            "rejections": w.rejections,
            "oos": {
                "total_return": str(w.oos_metrics.total_return),
                "sharpe": w.oos_metrics.sharpe,
                "max_drawdown": w.oos_metrics.max_drawdown,
                "trades": w.oos_metrics.trades,
                "profit_factor": w.oos_metrics.profit_factor,
            },
        }
        for w in result.windows
    ]
    extra: dict[str, Any] = {
        "walkforward": result.settings.to_dict(),
        "windows": windows_extra,
        "gate": [c.to_dict() for c in result.gate],
        "gate_verdict": gate_verdict(result.gate),
        "montecarlo": result.montecarlo.to_dict(),
        "montecarlo_daily": result.montecarlo_daily.to_dict(),
        "plateau": None if result.plateau is None else result.plateau.to_dict(),
        "inactive_pairs": [p.symbol for p in result.inactive_pairs],
        "open_at_end": [w.open_at_end for w in result.windows],
        "regimes": [r.to_dict() for r in result.regimes],
        "regimes_source": result.regimes_source,
        "full_sample": None if result.full_sample is None else result.full_sample.metrics.to_dict(),
        "unused_tail": None
        if result.unused_tail is None
        else [d.isoformat() for d in result.unused_tail],
    }
    return build_meta(
        strategy=result.strategy_name,
        timeframe=cfg.strategy.timeframe.value,
        pairs=[p.symbol for p in cfg.strategy.pairs],
        start=result.windows[0].window.oos_start.isoformat(),
        end=result.windows[-1].window.oos_end.isoformat(),
        include_holdout=cfg.backtest.include_holdout,
        params=result.base_params,
        data_files=result.data_files,
        duration_s=result.duration_s,
        root=root,
        extra=extra,
    )


def walkforward_artifacts(
    result: WalkForwardResult, run_id: str, root: Path, label: str | None = None
) -> RunArtifacts:
    meta = walkforward_meta(result, root)
    benchmarks = {BENCH_OOS: result.benchmark_metrics} if result.benchmark_metrics else {}
    benchmarks.update({f"{n} (OOS)": m for n, (_e, m) in result.extra_benchmarks.items()})
    bench_equities = {BENCH_OOS: result.benchmark_equity} if result.benchmark_equity else {}
    bench_equities.update({f"{n} (OOS)": e for n, (e, _m) in result.extra_benchmarks.items()})
    cfg = result.config
    return RunArtifacts(
        run_id=run_id,
        kind="WF",
        label=label or f"{result.strategy_name}-{cfg.strategy.timeframe.value}-wf-{result.mode}",
        config={
            **frozen_config(cfg, date_to_ms(result.windows[0].window.is_start), result.end_ms),
            "validation": result.settings.to_config_dict(),
        },
        metrics=result.oos_metrics.to_dict(),
        benchmarks={k: v.to_dict() for k, v in benchmarks.items()},
        meta=meta,
        report_md=render_walkforward_report(result, run_id, meta, root),
        trades_csv=trades_csv(result.oos_trades),
        equity_csv=equity_csv(result.oos_equity, bench_equities),
        equity_png=plot_equity(
            result.oos_equity, bench_equities, f"{run_id} {result.strategy_name} OOS concatenado"
        ),
    )


def register_walkforward(
    result: WalkForwardResult, root: Path, experiments_dir: Path, label: str | None = None
) -> Path:
    return register_artifacts(
        lambda run_id: walkforward_artifacts(result, run_id, root, label), experiments_dir, "WF"
    )


# ----------------------------------------------------------------------------- optimización


def _trials_table(result: OptimizationResult, limit: int = 10) -> str:
    ordered = sorted(result.trials, key=lambda t: t.score, reverse=True)[:limit]
    rows = "\n".join(
        f"| {t.number + 1} | {_num(t.score, 3)} | {_pct(t.total_return)} | {_num(t.sharpe)} | "
        f"{_pct(t.max_drawdown)} | {'-' if t.trades is None else t.trades} | {_num(t.profit_factor)} | "
        f"{_changes(t.params)} |"
        for t in ordered
    )
    return (
        "| Trial | Score | Retorno IS | Sharpe | Max DD | Trades | PF | Parámetros |\n"
        f"|---|---|---|---|---|---|---|---|\n{rows}"
    )


def render_optimization_report(
    run: OptimizationRun, run_id: str, meta: ExperimentMeta, root: Path
) -> str:
    cfg = run.config
    res = run.result
    best = run.best_run
    s = res.settings
    base = best.strategy.params.model_dump(mode="json")
    space_rows = "\n".join(
        f"| `{k}` | {v} | `{res.best_params.get(k, '—')}` |" for k, v in res.space.items()
    )
    return f"""# {run_id} — {best.strategy.name} {cfg.strategy.timeframe.value} optimización IS {ms_to_date(best.start_ms)} -> {ms_to_date(best.end_ms)}

> Sección autogenerada por `tradingbot optimize`. Solo **Notas y veredicto** se escribe a mano.
> **Métricas in-sample**: sirven para elegir parámetros, no como evidencia. La evidencia es la curva OOS del walk-forward.

## Configuración

- Estrategia: `{best.strategy.name}` · spec: `{spec_path(best.strategy.name, root) or "—"}`
- Datos: {data_line(cfg, best.start_ms, best.end_ms, best.warmup, meta.data_hash, best.activation, best.inactive)}
- Costos: {costs_line(cfg)}
- Riesgo: {risk_line(cfg)}
- Optimización: optuna TPE, {s.trials} trials ({res.completed} válidos), semilla {s.seed}, objetivo `{s.objective}`, min_trades {s.min_trades}, {res.duration_s:.0f} s
- Reproducibilidad: {_reproducibility(meta)}

## Espacio y mejores parámetros (score {_num(res.best_score, 3)})

| Parámetro | Espacio | Mejor |
|---|---|---|
{space_rows}

{_params_table(base)}

## Métricas de los mejores parámetros sobre el IS

{metrics_table(best.metrics, {k: v.metrics for k, v in best.benchmarks.items()})}

## Mejores 10 trials

{_trials_table(res)}

## Gráficos

`equity.png`, `trades.csv`, `equity.csv` corresponden a la corrida IS con los mejores parámetros.

## Notas y veredicto

- **Veredicto**: pendiente
- **Por qué**:
- **Qué se aprendió**:
- **Siguiente experimento propuesto**:
"""


def optimization_artifacts(
    run: OptimizationRun, run_id: str, root: Path, label: str | None = None
) -> RunArtifacts:
    best = run.best_run
    cfg = run.config
    meta = build_meta(
        strategy=best.strategy.name,
        timeframe=cfg.strategy.timeframe.value,
        pairs=[p.symbol for p in cfg.strategy.pairs],
        start=ms_to_date(best.start_ms),
        end=ms_to_date(best.end_ms),
        include_holdout=cfg.backtest.include_holdout,
        params=best.strategy.params.model_dump(mode="json"),
        data_files=best.data_files,
        duration_s=run.result.duration_s + best.duration_s,
        root=root,
        extra={
            "optimization": run.result.to_dict(),
            "trials": [t.to_dict() for t in run.result.trials],
        },
    )
    bench_equities = {k: v.equity for k, v in best.benchmarks.items()}
    return RunArtifacts(
        run_id=run_id,
        kind="OPT",
        label=label
        or f"{best.strategy.name}-{cfg.strategy.timeframe.value}-{run.result.settings.objective}",
        config=frozen_config(cfg, best.start_ms, best.end_ms),
        metrics=best.metrics.to_dict(),
        benchmarks={k: v.metrics.to_dict() for k, v in best.benchmarks.items()},
        meta=meta,
        report_md=render_optimization_report(run, run_id, meta, root),
        trades_csv=trades_csv(best.trades),
        equity_csv=equity_csv(best.equity, bench_equities),
        equity_png=plot_equity(best.equity, bench_equities, f"{run_id} {best.strategy.name} IS"),
    )


def register_optimization(
    run: OptimizationRun, root: Path, experiments_dir: Path, label: str | None = None
) -> Path:
    return register_artifacts(
        lambda run_id: optimization_artifacts(run, run_id, root, label), experiments_dir, "OPT"
    )
