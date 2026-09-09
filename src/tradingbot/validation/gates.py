"""Gate 1 (backtest → paper) como tabla criterio / umbral / valor / resultado (ADR-0008).

Los umbrales viven acá y en `docs/GATES.md`; si cambian, cambian en los dos lugares.
`passed=None` significa "no evaluable con esta corrida" (p. ej. regímenes por año en modo
optimizado), y no cuenta como aprobado.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from tradingbot.backtest.metrics import Metrics
from tradingbot.validation.regimes import RegimeCheck


@dataclass(frozen=True, slots=True)
class GateThresholds:
    sharpe_min: float = 0.8
    profit_factor_min: float = 1.3
    max_drawdown_max: float = 0.25
    drawdown_vs_benchmark_max: float = 0.5  # DD OOS <= 50 % del DD de B&H BTC
    positive_windows_min: float = 0.6
    trades_full_min: int = 100
    trades_oos_min: int = 40
    plateau_pass_min: float = 0.8
    montecarlo_dd_p95_max: float = 0.35


@dataclass(frozen=True, slots=True)
class GateCheck:
    name: str
    threshold: str
    value: str
    passed: bool | None
    note: str = ""

    @property
    def mark(self) -> str:
        return "n/a" if self.passed is None else ("OK" if self.passed else "FALLA")

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "name": self.name,
            "threshold": self.threshold,
            "value": self.value,
            "passed": self.passed,
            "note": self.note,
        }


def _fmt(value: float | Decimal | None, digits: int = 2, pct: bool = False) -> str:
    if value is None:
        return "-"
    number = float(value)
    return f"{number * 100:.{digits}f} %" if pct else f"{number:.{digits}f}"


def evaluate_gate1(
    *,
    oos: Metrics,
    benchmark: Metrics | None,
    window_returns: Sequence[Decimal],
    full_sample_trades: int | None,
    regimes: Sequence[RegimeCheck],
    regimes_source: str,
    plateau_pass_rate: float | None,
    montecarlo_dd_p95: float | None,
    thresholds: GateThresholds | None = None,
    inactive_pairs: Sequence[str] = (),
    universe: int | None = None,
) -> list[GateCheck]:
    t = thresholds or GateThresholds()
    checks: list[GateCheck] = []

    sharpe = oos.sharpe
    bench_sharpe = benchmark.sharpe if benchmark is not None else None
    # Sin B&H BTC el criterio relativo no se puede evaluar: n/a, nunca aprobado por defecto.
    sharpe_ok: bool | None
    if bench_sharpe is None or sharpe is None:
        sharpe_ok = None if bench_sharpe is None else False
    else:
        sharpe_ok = sharpe >= t.sharpe_min and sharpe >= bench_sharpe
    checks.append(
        GateCheck(
            "Sharpe OOS",
            f">= {t.sharpe_min} y >= B&H BTC ({_fmt(bench_sharpe)})",
            _fmt(sharpe),
            sharpe_ok,
            note="" if bench_sharpe is not None else "sin B&H BTC en el rango",
        )
    )
    pf = oos.profit_factor
    checks.append(
        GateCheck(
            "Profit factor OOS",
            f">= {t.profit_factor_min}",
            _fmt(pf),
            pf is not None and pf >= t.profit_factor_min,
        )
    )
    bench_dd = benchmark.max_drawdown if benchmark is not None else None
    dd_ok: bool | None
    if bench_dd is None:
        dd_ok = None
    else:
        dd_ok = (
            oos.max_drawdown <= t.max_drawdown_max
            and oos.max_drawdown <= t.drawdown_vs_benchmark_max * bench_dd
        )
    checks.append(
        GateCheck(
            "Max DD OOS",
            f"<= {t.max_drawdown_max * 100:.0f} % y <= {t.drawdown_vs_benchmark_max * 100:.0f} % "
            f"del DD B&H ({_fmt(bench_dd, pct=True)})",
            _fmt(oos.max_drawdown, pct=True),
            dd_ok,
            note="" if bench_dd is not None else "sin B&H BTC en el rango",
        )
    )
    active = None if universe is None else universe - len(inactive_pairs)
    checks.append(
        GateCheck(
            "Universo activo en OOS",
            "todos los pares con datos en todas las ventanas",
            "-" if active is None else f"{active}/{universe}",
            None if universe is None else not inactive_pairs,
            note=", ".join(inactive_pairs),
        )
    )
    positive = sum(1 for r in window_returns if r > 0)
    share = positive / len(window_returns) if window_returns else None
    checks.append(
        GateCheck(
            "Ventanas OOS positivas",
            f">= {t.positive_windows_min * 100:.0f} %",
            f"{positive}/{len(window_returns)}"
            + (f" ({share * 100:.0f} %)" if share is not None else ""),
            None if share is None else share >= t.positive_windows_min,
            note="secundario",
        )
    )
    checks.append(
        GateCheck(
            "Trades muestra completa",
            f">= {t.trades_full_min}",
            "-" if full_sample_trades is None else str(full_sample_trades),
            None if full_sample_trades is None else full_sample_trades >= t.trades_full_min,
            note="" if full_sample_trades is not None else "solo en modo fijo",
        )
    )
    checks.append(
        GateCheck(
            "Trades curva OOS",
            f">= {t.trades_oos_min}",
            str(oos.trades),
            oos.trades >= t.trades_oos_min,
        )
    )
    for regime in regimes:
        checks.append(
            GateCheck(
                f"Régimen: {regime.label}",
                regime.threshold,
                regime.value,
                regime.passed,
                note=regimes_source,
            )
        )
    checks.append(
        GateCheck(
            "Meseta ±20 %",
            f">= {t.plateau_pass_min * 100:.0f} % de variantes con PF > 1.1 y retorno > 0",
            _fmt(plateau_pass_rate, pct=True),
            None if plateau_pass_rate is None else plateau_pass_rate >= t.plateau_pass_min,
            note="" if plateau_pass_rate is not None else "correr con --plateau",
        )
    )
    checks.append(
        GateCheck(
            "Monte Carlo DD p95",
            f"<= {t.montecarlo_dd_p95_max * 100:.0f} %",
            _fmt(montecarlo_dd_p95, pct=True),
            None if montecarlo_dd_p95 is None else montecarlo_dd_p95 <= t.montecarlo_dd_p95_max,
        )
    )
    checks.append(
        GateCheck("Holdout", "PF > 1.1 y DD <= 25 %", "-", None, note="una sola vez, al final")
    )
    return checks


def gate_verdict(checks: Sequence[GateCheck]) -> str:
    """`aprobado` si todo lo evaluable pasa y no queda nada pendiente salvo el holdout."""
    failed = [c for c in checks if c.passed is False]
    pending = [c for c in checks if c.passed is None and c.name != "Holdout"]
    if failed:
        return f"no aprobado ({len(failed)} criterios fallan)"
    if pending:
        return f"incompleto ({len(pending)} criterios sin evaluar)"
    return "aprobado (falta el holdout)"
