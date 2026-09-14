"""Meseta de parámetros (ADR-0008): ±20 % uno a la vez y vértices del hipercubo.

Una estrategia robusta no depende de un punto exacto del espacio: la mayoría de las variantes
cercanas tiene que seguir siendo rentable. Cada variante es un backtest de rango completo.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from tradingbot.backtest.metrics import Metrics
from tradingbot.domain.errors import TradingBotError
from tradingbot.strategy.base import FloatRange, IntRange, ParamRange

PASS_PROFIT_FACTOR = 1.1
RELATIVE_SHARPE_FRACTION = 0.5


def _bump(value: Any, space: ParamRange, sign: int, pct: float) -> Any:
    """`value × (1 ± pct)` cuantizado al paso del espacio y acotado a sus límites."""
    if isinstance(space, IntRange):
        raw = float(value) * (1 + sign * pct)
        steps = round((raw - space.low) / space.step)
        return int(min(space.high, max(space.low, space.low + steps * space.step)))
    if isinstance(space, FloatRange):
        raw = float(value) * (1 + sign * pct)
        steps = round((raw - space.low) / space.step)
        return round(min(space.high, max(space.low, space.low + steps * space.step)), 3)
    return value


def variations(
    base: Mapping[str, Any], space: Mapping[str, ParamRange], pct: float = 0.2
) -> list[dict[str, Any]]:
    """Variantes distintas del base: 2 por parámetro numérico + 2^k vértices (sin duplicados)."""
    numeric = [
        name
        for name, rng in space.items()
        if name in base and isinstance(rng, IntRange | FloatRange)
    ]
    seen: set[tuple[tuple[str, Any], ...]] = {tuple(sorted(base.items()))}
    out: list[dict[str, Any]] = []

    def add(candidate: dict[str, Any]) -> None:
        key = tuple(sorted(candidate.items()))
        if key not in seen:
            seen.add(key)
            out.append(candidate)

    for name in numeric:
        for sign in (-1, 1):
            add({**base, name: _bump(base[name], space[name], sign, pct)})
    if len(numeric) > 1:
        for signs in itertools.product((-1, 1), repeat=len(numeric)):
            candidate = dict(base)
            for name, sign in zip(numeric, signs, strict=True):
                candidate[name] = _bump(base[name], space[name], sign, pct)
            add(candidate)
    return out


@dataclass(frozen=True, slots=True)
class PlateauRow:
    params: dict[str, Any]
    total_return: Decimal | None
    profit_factor: float | None
    trades: int | None
    passed: bool
    error: str = ""
    sharpe: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "params": self.params,
            "total_return": None if self.total_return is None else str(self.total_return),
            "profit_factor": self.profit_factor,
            "trades": self.trades,
            "sharpe": self.sharpe,
            "passed": self.passed,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class PlateauResult:
    base_params: dict[str, Any]
    pct: float
    rows: list[PlateauRow]
    warnings: list[str] = field(default_factory=list)
    base_sharpe: float | None = None

    @property
    def pass_rate(self) -> float | None:
        return sum(1 for r in self.rows if r.passed) / len(self.rows) if self.rows else None

    @property
    def relative_pass_rate(self) -> float | None:
        """Informativo (no gate): variantes con Sharpe >= 0.5 x el Sharpe base.

        Un criterio absoluto laxo (PF > 1.1) puede dar 100 % con retornos de +7 % a +277 %.
        """
        if not self.rows or self.base_sharpe is None or self.base_sharpe <= 0:
            return None
        floor = RELATIVE_SHARPE_FRACTION * self.base_sharpe
        hits = sum(1 for r in self.rows if r.sharpe is not None and r.sharpe >= floor)
        return hits / len(self.rows)

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_params": self.base_params,
            "pct": self.pct,
            "pass_rate": self.pass_rate,
            "base_sharpe": self.base_sharpe,
            "relative_pass_rate": self.relative_pass_rate,
            "warnings": self.warnings,
            "rows": [r.to_dict() for r in self.rows],
        }


def run_plateau(
    base: Mapping[str, Any],
    space: Mapping[str, ParamRange],
    run_fn: Callable[[Mapping[str, Any]], Metrics],
    *,
    pct: float = 0.2,
    only: Sequence[str] | None = None,
    progress: Callable[[str], None] | None = None,
    base_metrics: Metrics | None = None,
) -> PlateauResult:
    """Corre cada variante; una variante inválida cuenta como fallida (no como ausente)."""
    subspace = {k: v for k, v in space.items() if only is None or k in only}
    warnings = [
        f"{name}={base[name]} fuera del espacio [{rng.low}, {rng.high}]: las variantes se acotan"
        for name, rng in subspace.items()
        if name in base
        and isinstance(rng, IntRange | FloatRange)
        and not (rng.low <= base[name] <= rng.high)
    ]
    rows: list[PlateauRow] = []
    candidates = variations(base, subspace, pct)
    for i, params in enumerate(candidates, start=1):
        changed = {k: v for k, v in params.items() if base.get(k) != v}
        if progress:
            progress(f"meseta {i}/{len(candidates)}: {changed}")
        try:
            metrics = run_fn(params)
        except (ValidationError, TradingBotError) as exc:
            rows.append(PlateauRow(dict(params), None, None, None, False, error=str(exc)[:120]))
            continue
        passed = (
            metrics.profit_factor is not None
            and metrics.profit_factor > PASS_PROFIT_FACTOR
            and metrics.total_return > 0
        )
        rows.append(
            PlateauRow(
                dict(params),
                metrics.total_return,
                metrics.profit_factor,
                metrics.trades,
                passed,
                sharpe=metrics.sharpe,
            )
        )
    return PlateauResult(
        base_params=dict(base),
        pct=pct,
        rows=rows,
        warnings=warnings,
        base_sharpe=None if base_metrics is None else base_metrics.sharpe,
    )
