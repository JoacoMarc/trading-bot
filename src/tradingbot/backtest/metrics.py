"""Métricas de una corrida a partir de la curva de equity, los trades y los fills.

Convenciones (PLAN §Fase 4): Sharpe y Sortino sobre retornos **diarios** (equity remuestreada al
último valor de cada día UTC, rf = 0, anualización √365); CAGR con años de 365.25 días; max
drawdown sobre la equity mark-to-market de cada `Bar`. Dinero en Decimal; ratios en float.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

from tradingbot.domain.money import ZERO
from tradingbot.domain.orders import Fill
from tradingbot.domain.positions import Trade

EquityPoint = tuple[int, Decimal]  # (ts ms UTC, equity)
DAY_MS = 86_400_000
_ANNUALIZATION = math.sqrt(365.0)


@dataclass(frozen=True, slots=True)
class Metrics:
    start_ts: int
    end_ts: int
    days: float
    bars: int
    initial_equity: Decimal
    final_equity: Decimal
    total_return: Decimal
    cagr: float | None
    sharpe: float | None
    sortino: float | None
    calmar: float | None
    max_drawdown: float
    longest_underwater_days: float  # tramo más largo pico → recuperación (no el del DD máximo)
    trades: int
    win_rate: float | None
    profit_factor: float | None
    expectancy: Decimal | None
    avg_trade_hours: float | None
    exposure: float
    fees_quote: Decimal
    avg_shortfall_bps: float | None
    exits: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Serializable a JSON: Decimal como string exacto; NaN/inf como None."""
        out: dict[str, Any] = {}
        for key, value in asdict(self).items():
            if isinstance(value, Decimal):
                out[key] = str(value)
            elif isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                out[key] = None
            else:
                out[key] = value
        return out


def _equity_series(equity: Sequence[EquityPoint]) -> pd.Series:
    index = pd.to_datetime([ts for ts, _ in equity], unit="ms", utc=True)
    return pd.Series([float(v) for _, v in equity], index=index, dtype="float64")


def _ratio(mean: float, deviation: float) -> float | None:
    if deviation <= 0.0 or math.isnan(deviation):
        return None
    return float(mean / deviation * _ANNUALIZATION)


def _year_of(ts_ms: int) -> int:
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).year


def daily_returns(equity: Sequence[EquityPoint]) -> pd.Series:
    """Retornos entre cierres de día UTC (último equity de cada día)."""
    series = _equity_series(equity)
    daily = series.resample("1D").last().dropna()
    returns: pd.Series = daily.pct_change().dropna()
    return returns


def drawdown_series(equity: Sequence[EquityPoint]) -> np.ndarray:
    """Drawdown de cada punto respecto del pico corriente (≤ 0)."""
    values = np.array([float(v) for _, v in equity], dtype=np.float64)
    if values.size == 0:
        return values
    peaks = np.maximum.accumulate(values)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(peaks > 0, values / peaks - 1.0, 0.0)


def max_drawdown(equity: Sequence[EquityPoint]) -> tuple[float, float]:
    """(profundidad máxima como fracción positiva, días del tramo más largo bajo agua).

    El segundo valor mide el período pico → recuperación más largo, que no necesariamente es
    el del drawdown más profundo.
    """
    if len(equity) < 2:
        return 0.0, 0.0
    values = np.array([float(v) for _, v in equity])
    times = np.array([ts for ts, _ in equity], dtype=np.int64)
    peaks = np.maximum.accumulate(values)
    drawdowns = drawdown_series(equity)
    depth = float(-drawdowns.min()) if drawdowns.size else 0.0

    longest_ms = 0
    start: int | None = None
    for i in range(values.size):
        under_water = values[i] < peaks[i]
        if under_water and start is None:
            start = int(times[i - 1]) if i > 0 else int(times[i])
        elif not under_water and start is not None:
            longest_ms = max(longest_ms, int(times[i]) - start)
            start = None
    if start is not None:
        longest_ms = max(longest_ms, int(times[-1]) - start)
    return depth, longest_ms / DAY_MS


def compute_metrics(
    equity: Sequence[EquityPoint],
    invested: Sequence[bool],
    trades: Sequence[Trade],
    fills: Sequence[Fill],
) -> Metrics:
    """Métricas completas. `invested[i]` dice si en el `Bar` i había posición abierta."""
    if not equity:
        msg = "se necesita al menos un punto de equity"
        raise ValueError(msg)
    if len(invested) != len(equity):
        msg = f"invested ({len(invested)}) y equity ({len(equity)}) deben tener la misma longitud"
        raise ValueError(msg)

    start_ts, initial = equity[0]
    end_ts, final = equity[-1]
    days = max((end_ts - start_ts) / DAY_MS, 0.0)
    total_return = final / initial - 1 if initial > ZERO else ZERO

    cagr: float | None = None
    if days > 0 and initial > ZERO and final > ZERO:
        cagr = float(final / initial) ** (365.25 / days) - 1.0

    returns = daily_returns(equity)
    sharpe = sortino = None
    if len(returns) >= 2:
        mean = float(returns.mean())
        sharpe = _ratio(mean, float(returns.std(ddof=1)))
        downside = float(np.sqrt(np.mean(np.square(np.minimum(returns.to_numpy(), 0.0)))))
        sortino = _ratio(mean, downside)

    depth, underwater_days = max_drawdown(equity)
    calmar = cagr / depth if cagr is not None and depth > 0 else None

    wins = [t for t in trades if t.pnl > ZERO]
    losses = [t for t in trades if t.pnl <= ZERO]
    gross_win = sum((t.pnl for t in wins), ZERO)
    gross_loss = -sum((t.pnl for t in losses), ZERO)
    win_rate = len(wins) / len(trades) if trades else None
    profit_factor = float(gross_win / gross_loss) if gross_loss > ZERO else None
    expectancy = sum((t.pnl for t in trades), ZERO) / len(trades) if trades else None
    avg_hours = sum(t.duration_ms for t in trades) / len(trades) / 3_600_000 if trades else None
    exposure = sum(1 for flag in invested if flag) / len(invested)
    fees = sum((f.fee_in_quote() for f in fills), ZERO)
    shortfalls = [float(f.shortfall_bps) for f in fills]
    avg_shortfall = float(np.mean(shortfalls)) if shortfalls else None
    exits = dict(sorted(Counter(t.exit_reason.value for t in trades).items()))

    return Metrics(
        start_ts=start_ts,
        end_ts=end_ts,
        days=days,
        bars=len(equity),
        initial_equity=initial,
        final_equity=final,
        total_return=total_return,
        cagr=cagr,
        sharpe=sharpe,
        sortino=sortino,
        calmar=calmar,
        max_drawdown=depth,
        longest_underwater_days=underwater_days,
        trades=len(trades),
        win_rate=win_rate,
        profit_factor=profit_factor,
        expectancy=expectancy,
        avg_trade_hours=avg_hours,
        exposure=exposure,
        fees_quote=fees,
        avg_shortfall_bps=avg_shortfall,
        exits=exits,
    )


def yearly_breakdown(
    equity: Sequence[EquityPoint], trades: Sequence[Trade]
) -> list[dict[str, Any]]:
    """Retorno, max drawdown y trades cerrados por año calendario UTC.

    El drawdown de cada año se mide contra el pico corriente de toda la serie (un pico en
    diciembre cuenta para el valle de enero), no solo contra los puntos de ese año.
    """
    if not equity:
        return []
    drawdowns = drawdown_series(equity)
    by_year: dict[int, list[int]] = {}
    for i, (ts, _) in enumerate(equity):
        by_year.setdefault(_year_of(ts), []).append(i)
    rows: list[dict[str, Any]] = []
    previous_close: Decimal | None = None
    for year in sorted(by_year):
        indices = by_year[year]
        first = previous_close if previous_close is not None else equity[indices[0]][1]
        last = equity[indices[-1]][1]
        depth = float(-min(drawdowns[i] for i in indices))
        year_trades = [t for t in trades if _year_of(t.exit_time) == year]
        rows.append(
            {
                "year": year,
                "return": float(last / first - 1) if first > ZERO else 0.0,
                "max_drawdown": depth,
                "trades": len(year_trades),
                "pnl": str(sum((t.pnl for t in year_trades), ZERO)),
            }
        )
        previous_close = last
    return rows
