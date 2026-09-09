"""Regímenes por año calendario (ADR-0008): retorno y drawdown intra-año.

A diferencia de `metrics.yearly_breakdown` (DD contra el pico corriente de toda la corrida), acá
el pico se reinicia al empezar cada año: mide el daño *dentro* del año, que es lo que pregunta el
criterio "ningún año con DD > 25 %" del gate.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from tradingbot.backtest.metrics import EquityPoint
from tradingbot.domain.money import ZERO
from tradingbot.domain.positions import Trade


@dataclass(frozen=True, slots=True)
class YearRegime:
    year: int
    total_return: Decimal
    max_drawdown: float  # intra-año
    trades: int
    pnl: Decimal
    complete: bool  # el año tiene datos desde enero y hasta diciembre

    def to_dict(self) -> dict[str, str | int | float | bool]:
        return {
            "year": self.year,
            "total_return": str(self.total_return),
            "max_drawdown": self.max_drawdown,
            "trades": self.trades,
            "pnl": str(self.pnl),
            "complete": self.complete,
        }


def _year(ts_ms: int) -> int:
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).year


def _day_of_year(ts_ms: int) -> int:
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).timetuple().tm_yday


COMPLETE_START_MAX_DAY = 7  # primer punto dentro de la primera semana
COMPLETE_END_MIN_DAY = 359  # último punto dentro de la última semana


def yearly_regimes(equity: Sequence[EquityPoint], trades: Sequence[Trade]) -> list[YearRegime]:
    """Una fila por año con datos. El retorno usa como base la última equity del año anterior."""
    if not equity:
        return []
    by_year: dict[int, list[EquityPoint]] = {}
    for point in equity:
        by_year.setdefault(_year(point[0]), []).append(point)
    trades_by_year: dict[int, list[Trade]] = {}
    for trade in trades:
        trades_by_year.setdefault(_year(trade.exit_time), []).append(trade)

    rows: list[YearRegime] = []
    previous_close: Decimal | None = None
    for year in sorted(by_year):
        points = by_year[year]
        base = previous_close if previous_close is not None else points[0][1]
        peak = base
        max_dd = 0.0
        for _, value in points:
            peak = max(peak, value)
            if peak > ZERO:
                max_dd = max(max_dd, float((peak - value) / peak))
        last = points[-1][1]
        total_return = (last / base - 1) if base > ZERO else ZERO
        year_trades = trades_by_year.get(year, [])
        rows.append(
            YearRegime(
                year=year,
                total_return=total_return,
                max_drawdown=max_dd,
                trades=len(year_trades),
                pnl=sum((t.pnl for t in year_trades), ZERO),
                complete=_day_of_year(points[0][0]) <= COMPLETE_START_MAX_DAY
                and _day_of_year(points[-1][0]) >= COMPLETE_END_MIN_DAY,
            )
        )
        previous_close = last
    return rows


@dataclass(frozen=True, slots=True)
class RegimeRules:
    """Criterios por año del Gate 1 (docs/GATES.md)."""

    positive_years: tuple[int, ...] = (2020, 2021, 2023, 2024)
    max_loss_by_year: Mapping[int, Decimal] | None = None  # default: {2022: -8 %}
    max_yearly_drawdown: float = 0.25

    @property
    def losses(self) -> Mapping[int, Decimal]:
        return (
            self.max_loss_by_year if self.max_loss_by_year is not None else {2022: Decimal("-0.08")}
        )


@dataclass(frozen=True, slots=True)
class RegimeCheck:
    label: str
    threshold: str
    value: str
    passed: bool | None  # None: el año no está en la muestra


def _year_value(row: YearRegime | None) -> tuple[str, bool]:
    """Texto y si el año se puede evaluar (completo). Parcial → informativo, no aprobado."""
    if row is None:
        return "sin datos", False
    text = f"{row.total_return * 100:+.2f} %"
    return (text, True) if row.complete else (f"parcial ({text})", False)


def check_regimes(
    rows: Sequence[YearRegime], rules: RegimeRules | None = None
) -> list[RegimeCheck]:
    rules = rules or RegimeRules()
    by_year = {r.year: r for r in rows}
    checks: list[RegimeCheck] = []
    for year in rules.positive_years:
        row = by_year.get(year)
        value, evaluable = _year_value(row)
        passed = row.total_return > ZERO if row is not None and evaluable else None
        checks.append(RegimeCheck(f"retorno {year}", "> 0", value, passed))
    for year, floor in rules.losses.items():
        row = by_year.get(year)
        value, evaluable = _year_value(row)
        passed = row.total_return >= floor if row is not None and evaluable else None
        checks.append(RegimeCheck(f"retorno {year}", f">= {floor * 100:+.0f} %", value, passed))
    if rows:
        worst = max(rows, key=lambda r: r.max_drawdown)
        checks.append(
            RegimeCheck(
                "max DD intra-año",
                f"<= {rules.max_yearly_drawdown * 100:.0f} %",
                f"{worst.max_drawdown * 100:.2f} % ({worst.year})",
                worst.max_drawdown <= rules.max_yearly_drawdown,
            )
        )
    else:
        checks.append(
            RegimeCheck(
                "max DD intra-año", f"<= {rules.max_yearly_drawdown * 100:.0f} %", "sin datos", None
            )
        )
    return checks
