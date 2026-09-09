"""Regímenes por año (DD intra-año) y tabla del Gate 1 (ADR-0008)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tests.factories import d
from tests.validation.factories import make_metrics
from tradingbot.validation.gates import GateThresholds, evaluate_gate1, gate_verdict
from tradingbot.validation.regimes import RegimeCheck, YearRegime, check_regimes, yearly_regimes


def ts(year: int, month: int, day: int) -> int:
    return int(datetime(year, month, day, tzinfo=UTC).timestamp() * 1000)


def test_yearly_regimes_reset_the_peak_each_year() -> None:
    equity = [
        (ts(2023, 12, 1), d("100")),
        (ts(2023, 12, 10), d("150")),
        (ts(2023, 12, 20), d("120")),  # 2023: +20 %, DD 20 % (150 -> 120)
        (ts(2024, 1, 10), d("108")),  # 2024: base 120; DD intra-año 10 %, no 28 % desde 150
        (ts(2024, 2, 10), d("132")),  # 2024: +10 %
    ]
    rows = yearly_regimes(equity, [])
    assert [r.year for r in rows] == [2023, 2024]
    assert rows[0].total_return == d("0.2")
    assert rows[0].max_drawdown == 0.2
    assert rows[1].total_return == d("0.1")
    assert rows[1].max_drawdown == 0.1
    assert not rows[0].complete
    assert not rows[1].complete
    assert rows[1].trades == 0
    assert rows[1].pnl == 0


def _regime(year: int, ret: str, dd: float) -> YearRegime:
    return YearRegime(year, Decimal(ret), dd, 10, Decimal(0), True)


def test_check_regimes_rules_and_missing_years() -> None:
    rows = [
        _regime(2020, "0.25", 0.06),
        _regime(2021, "0.13", 0.05),
        _regime(2022, "-0.05", 0.04),
        _regime(2023, "0.02", 0.04),
        _regime(2024, "0.11", 0.07),
    ]
    checks = check_regimes(rows)
    by_label = {c.label: c for c in checks}
    assert all(by_label[f"retorno {y}"].passed for y in (2020, 2021, 2023, 2024))
    assert by_label["retorno 2022"].passed is True
    assert by_label["max DD intra-año"].passed is True
    assert "2024" in by_label["max DD intra-año"].value
    worse = check_regimes([_regime(2022, "-0.09", 0.30)])
    labels = {c.label: c for c in worse}
    assert labels["retorno 2022"].passed is False
    assert labels["max DD intra-año"].passed is False
    assert labels["retorno 2020"].passed is None  # sin datos: no evaluable, no aprobado


def _passing_regimes() -> list[RegimeCheck]:
    return [RegimeCheck("retorno 2020", "> 0", "+10 %", True)]


def test_gate1_verdicts() -> None:
    oos = make_metrics(sharpe=1.0, profit_factor=1.5, max_drawdown=0.10, trades=50)
    bench = make_metrics(sharpe=0.9, max_drawdown=0.5)
    checks = evaluate_gate1(
        oos=oos,
        benchmark=bench,
        window_returns=[d("0.1"), d("-0.02"), d("0.05"), d("0.03")],
        full_sample_trades=120,
        regimes=_passing_regimes(),
        regimes_source="muestra completa",
        plateau_pass_rate=0.9,
        montecarlo_dd_p95=0.2,
        thresholds=GateThresholds(),
        universe=2,
    )
    by_name = {c.name: c for c in checks}
    assert by_name["Sharpe OOS"].passed is True
    assert by_name["Max DD OOS"].passed is True  # 10 % <= 25 % y <= 50 % de 50 %
    assert by_name["Ventanas OOS positivas"].passed is True  # 3/4
    assert by_name["Holdout"].passed is None
    assert by_name["Universo activo en OOS"].passed is True
    assert gate_verdict(checks) == "aprobado (falta el holdout)"

    weak = evaluate_gate1(
        oos=make_metrics(sharpe=0.85, profit_factor=1.5, max_drawdown=0.30, trades=50),
        benchmark=bench,
        window_returns=[d("0.1")],
        full_sample_trades=120,
        regimes=_passing_regimes(),
        regimes_source="muestra completa",
        plateau_pass_rate=0.9,
        montecarlo_dd_p95=0.2,
    )
    assert {c.name for c in weak if c.passed is False} == {"Sharpe OOS", "Max DD OOS"}
    assert gate_verdict(weak) == "no aprobado (2 criterios fallan)"

    incomplete = evaluate_gate1(
        oos=oos,
        benchmark=None,
        window_returns=[d("0.1")],
        full_sample_trades=None,
        regimes=_passing_regimes(),
        regimes_source="curva OOS",
        plateau_pass_rate=None,
        montecarlo_dd_p95=0.2,
    )
    pending = {c.name for c in incomplete if c.passed is None}
    # Sin B&H BTC los criterios relativos no se evalúan: n/a, nunca aprobados por defecto.
    assert pending == {
        "Sharpe OOS",
        "Max DD OOS",
        "Trades muestra completa",
        "Meseta ±20 %",
        "Holdout",
        "Universo activo en OOS",
    }
    assert gate_verdict(incomplete).startswith("incompleto (5 criterios")
    with_inactive = evaluate_gate1(
        oos=oos,
        benchmark=bench,
        window_returns=[d("0.1")],
        full_sample_trades=120,
        regimes=_passing_regimes(),
        regimes_source="muestra completa",
        plateau_pass_rate=0.9,
        montecarlo_dd_p95=0.2,
        inactive_pairs=["SOL/USDT"],
        universe=8,
    )
    universe = next(c for c in with_inactive if c.name == "Universo activo en OOS")
    assert universe.passed is False
    assert universe.value == "7/8"
    assert "SOL/USDT" in universe.note


def test_partial_years_are_reported_but_not_evaluated() -> None:
    partial = YearRegime(2020, Decimal("0.3"), 0.05, 4, Decimal(0), False)
    checks = {c.label: c for c in check_regimes([partial, _regime(2021, "0.1", 0.04)])}
    assert checks["retorno 2020"].passed is None
    assert checks["retorno 2020"].value.startswith("parcial (+30.00 %)")
    assert checks["retorno 2021"].passed is True


def test_complete_year_needs_first_and_last_week() -> None:
    full_year = [
        (ts(2022, 1, 3), d("100")),
        (ts(2022, 6, 1), d("120")),
        (ts(2022, 12, 28), d("110")),
    ]
    late_start = [(ts(2022, 1, 20), d("100")), (ts(2022, 12, 28), d("110"))]
    assert yearly_regimes(full_year, [])[0].complete
    assert not yearly_regimes(late_start, [])[0].complete
