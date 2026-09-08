"""Test de equivalencia de estrategias: sin lookahead y paridad backtest/live.

Dos chequeos complementarios sobre una serie real de velas:

1. `check_no_lookahead`: la señal en la vela `t` calculada con datos hasta `t` debe ser idéntica
   a la calculada con datos hasta `t + horizon` evaluada en `t`. Detecta indicadores que miran el
   futuro (`shift(-1)`, máximos globales, normalizaciones sobre toda la serie).
2. `check_window_equivalence`: los indicadores en `t` calculados sobre toda la serie (backtest)
   deben coincidir, dentro de `rtol`, con los calculados sobre la ventana de `warmup_candles`
   que termina en `t` (live), **y la señal y el trailing en `t` deben ser los mismos**. Detecta
   warmups cortos, semillas que no convergen y reglas discontinuas (un cruce que ocurre en una
   serie y no en la otra).

Ambos devuelven un `EquivalenceReport`; `assert_equivalent` los combina para pytest.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

import numpy as np

from tradingbot.domain.enums import Side
from tradingbot.domain.money import to_decimal
from tradingbot.domain.orders import Signal, make_client_order_id
from tradingbot.domain.positions import Position
from tradingbot.indicators.core import FloatArray
from tradingbot.strategy.base import OhlcvArrays, Strategy, StrategyContext

DEFAULT_EQUITY = Decimal(10_000)
Decision = tuple[Signal, Decimal | None]


@dataclass(frozen=True, slots=True)
class EquivalenceReport:
    """Resultado de un chequeo: índices probados, peor diferencia por indicador y fallas."""

    check: str
    samples: tuple[int, ...]
    max_rel_diff: dict[str, float] = field(default_factory=dict)
    failures: tuple[str, ...] = ()
    signal_comparisons: int = 0
    signal_mismatches: int = 0

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def signal_match_rate(self) -> float:
        if self.signal_comparisons == 0:
            return 1.0
        return 1.0 - self.signal_mismatches / self.signal_comparisons

    def summary(self) -> str:
        status = "OK" if self.ok else f"{len(self.failures)} fallas"
        parts = [f"{self.check}: {status} sobre {len(self.samples)} muestras"]
        if self.signal_comparisons:
            parts.append(f"señales iguales {self.signal_match_rate:.1%}")
        if self.max_rel_diff:
            worst = ", ".join(f"{k}={v:.2e}" for k, v in sorted(self.max_rel_diff.items()))
            parts.append(f"peor diferencia {worst}")
        return "; ".join(parts)


def _sample_indices(
    strategy: Strategy, ohlcv: OhlcvArrays, samples: int, seed: int
) -> tuple[int, ...]:
    first = strategy.warmup_candles
    last = len(ohlcv) - 1
    if last < first:
        msg = f"se necesitan más de {first} velas (warmup) y hay {len(ohlcv)}"
        raise ValueError(msg)
    candidates = np.arange(first, last + 1)
    rng = np.random.default_rng(seed)
    chosen = rng.choice(candidates, size=min(samples, candidates.size), replace=False)
    return tuple(int(i) for i in sorted(chosen))


def _synthetic_position(strategy: Strategy, ohlcv: OhlcvArrays, index: int) -> Position:
    """Posición ficticia abierta unas velas antes de `index`, para ejercitar el camino de salida."""
    entry_index = max(index - 5, 0)
    entry_price = to_decimal(ohlcv.close[entry_index])
    highest = to_decimal(float(np.max(ohlcv.close[entry_index : index + 1])))
    return Position(
        pair=ohlcv.pair,
        strategy=strategy.name,
        qty=Decimal("1"),
        entry_price=entry_price,
        entry_time=int(ohlcv.open_time[entry_index]),
        stop_price=entry_price * Decimal("0.9"),
        highest_close_since_entry=highest,
        client_order_id=make_client_order_id(
            strategy.name, ohlcv.pair, int(ohlcv.open_time[entry_index]), Side.BUY
        ),
    )


def _decide(
    strategy: Strategy,
    ohlcv: OhlcvArrays,
    indicators: Mapping[str, FloatArray],
    index: int,
    position: Position | None,
) -> Decision:
    ctx = StrategyContext(
        ohlcv=ohlcv,
        indicators=indicators,
        index=index,
        position=position,
        equity=DEFAULT_EQUITY,
        cash=DEFAULT_EQUITY,
    )
    return strategy.on_candle(ctx), strategy.trailing_stop(ctx)


def signal_at(
    strategy: Strategy,
    ohlcv: OhlcvArrays,
    index: int,
    position: Position | None = None,
) -> Decision:
    """Señal y trailing stop en `index` con los indicadores calculados sobre `ohlcv` completo."""
    return _decide(strategy, ohlcv, strategy.compute_indicators(ohlcv), index, position)


def _signals_equal(a: Signal, b: Signal) -> bool:
    if (a.action, a.pair, a.open_time, a.exit_reason, a.stop_price) != (
        b.action,
        b.pair,
        b.open_time,
        b.exit_reason,
        b.stop_price,
    ):
        return False
    if a.strength is None or b.strength is None:
        return a.strength is None and b.strength is None
    return math.isclose(a.strength, b.strength, rel_tol=1e-9, abs_tol=1e-12)


def _describe_mismatch(label: str, reference: Decision, other: Decision) -> list[str]:
    problems: list[str] = []
    signal_a, stop_a = reference
    signal_b, stop_b = other
    if not _signals_equal(signal_a, signal_b):
        problems.append(
            f"{label}: señal {signal_a.action.value} != {signal_b.action.value} "
            f"(stop {signal_a.stop_price} vs {signal_b.stop_price})"
        )
    if stop_a != stop_b:
        problems.append(f"{label}: trailing {stop_a} != {stop_b}")
    return problems


def check_no_lookahead(
    strategy: Strategy,
    ohlcv: OhlcvArrays,
    *,
    samples: int = 20,
    horizon: int = 50,
    seed: int = 0,
) -> EquivalenceReport:
    """La decisión en `t` no cambia cuando aparecen velas posteriores a `t`."""
    indices = _sample_indices(strategy, ohlcv, samples, seed)
    failures: list[str] = []
    comparisons = 0
    for t in indices:
        now = ohlcv.slice(0, t + 1)
        future = ohlcv.slice(0, min(len(ohlcv), t + 1 + horizon))
        now_indicators = strategy.compute_indicators(now)
        future_indicators = strategy.compute_indicators(future)
        scenarios = (
            ("sin posición", None),
            ("con posición", _synthetic_position(strategy, ohlcv, t)),
        )
        for label, position in scenarios:
            comparisons += 1
            reference = _decide(strategy, now, now_indicators, t, position)
            other = _decide(strategy, future, future_indicators, t, position)
            failures.extend(_describe_mismatch(f"t={t} {label}", reference, other))
    return EquivalenceReport(
        check="no_lookahead",
        samples=indices,
        failures=tuple(failures),
        signal_comparisons=comparisons,
        signal_mismatches=len(failures),
    )


def check_window_equivalence(
    strategy: Strategy,
    ohlcv: OhlcvArrays,
    *,
    samples: int = 20,
    rtol: float = 1e-4,
    atol: float = 1e-9,
    max_signal_mismatch_rate: float = 0.0,
    seed: int = 0,
) -> EquivalenceReport:
    """Indicadores y decisión en `t`: toda la serie (backtest) vs ventana de warmup (live).

    Los indicadores se comparan con `rtol`; las decisiones deben ser idénticas salvo la
    fracción `max_signal_mismatch_rate` (0 por defecto; el gate de paridad de la Fase 7 usa
    su propio umbral).
    """
    indices = _sample_indices(strategy, ohlcv, samples, seed)
    full = strategy.compute_indicators(ohlcv)
    warmup = strategy.warmup_candles
    worst: dict[str, float] = dict.fromkeys(full, 0.0)
    failures: list[str] = []
    mismatches: list[str] = []
    comparisons = 0
    for t in indices:
        window = ohlcv.slice(t - warmup + 1, t + 1)
        partial = strategy.compute_indicators(window)
        for name, series in full.items():
            a = float(series[t])
            b = float(partial[name][-1])
            if math.isnan(a) and math.isnan(b):
                continue
            if math.isnan(a) or math.isnan(b):
                failures.append(f"t={t} {name}: NaN solo en una de las dos series ({a} vs {b})")
                continue
            diff = abs(a - b)
            rel = diff / max(abs(a), atol)
            worst[name] = max(worst[name], rel)
            if diff > atol + rtol * abs(a):
                failures.append(
                    f"t={t} {name}: serie completa {a!r} vs ventana {b!r} (rel {rel:.2e})"
                )
        scenarios = (
            ("sin posición", None),
            ("con posición", _synthetic_position(strategy, ohlcv, t)),
        )
        for label, position in scenarios:
            comparisons += 1
            reference = _decide(strategy, ohlcv, full, t, position)
            other = _decide(strategy, window, partial, len(window) - 1, position)
            mismatches.extend(_describe_mismatch(f"t={t} {label}", reference, other))
    if comparisons and len(mismatches) / comparisons > max_signal_mismatch_rate:
        failures.extend(mismatches)
    return EquivalenceReport(
        check="window_equivalence",
        samples=indices,
        max_rel_diff=worst,
        failures=tuple(failures),
        signal_comparisons=comparisons,
        signal_mismatches=len(mismatches),
    )


def assert_equivalent(
    strategy: Strategy,
    ohlcv: OhlcvArrays,
    *,
    samples: int = 20,
    rtol: float = 1e-4,
    seed: int = 0,
) -> tuple[EquivalenceReport, EquivalenceReport]:
    """Corre ambos chequeos y lanza `AssertionError` con el detalle si alguno falla."""
    reports = (
        check_no_lookahead(strategy, ohlcv, samples=samples, seed=seed),
        check_window_equivalence(strategy, ohlcv, samples=samples, rtol=rtol, seed=seed),
    )
    problems = [f"{r.check}: {f}" for r in reports for f in r.failures]
    if problems:
        shown = "\n".join(problems[:10])
        more = f"\n... y {len(problems) - 10} más" if len(problems) > 10 else ""
        msg = f"{strategy.name} no pasa la equivalencia:\n{shown}{more}"
        raise AssertionError(msg)
    return reports
