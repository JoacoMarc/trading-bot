"""Comparación emparejada de retornos diarios, con bloques de30 días."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def daily_returns(equity: pd.DataFrame) -> pd.Series:
    values = pd.Series(
        equity.equity.to_numpy(dtype=float), index=pd.to_datetime(equity.ts, unit="ms", utc=True)
    )
    return values.resample("D").last().pct_change(fill_method=None).dropna()


def sharpe(values: np.ndarray) -> float:
    deviation = values.std(ddof=1)
    return float(values.mean() / deviation * np.sqrt(365)) if deviation > 0 else 0.0


def paired_comparison(
    base: pd.DataFrame,
    candidate: pd.DataFrame,
    *,
    runs: int = 5000,
    seed: int = 42,
    block_days: int = 30,
) -> dict[str, Any]:
    control, filtered = daily_returns(base), daily_returns(candidate)
    if not control.index.equals(filtered.index) or len(control) < 2 * block_days:
        raise ValueError("comparación requiere los mismos días y al menos dos bloques")
    x, y = control.to_numpy(), filtered.to_numpy()
    rng = np.random.default_rng(seed)
    changes = np.empty(runs)
    for n in range(runs):
        starts = rng.integers(0, len(x), size=int(np.ceil(len(x) / block_days)))
        indices = ((starts[:, None] + np.arange(block_days)) % len(x)).ravel()[: len(x)]
        changes[n] = sharpe(y[indices]) - sharpe(x[indices])

    def drawdown(values: np.ndarray) -> float:
        curve = np.r_[values[0], values]
        return float(np.max(1 - curve / np.maximum.accumulate(curve)))

    delta = sharpe(y) - sharpe(x)
    lower, upper = np.quantile(changes, [0.025, 0.975])
    base_dd, candidate_dd = (
        drawdown(base.equity.to_numpy(dtype=float)),
        drawdown(candidate.equity.to_numpy(dtype=float)),
    )
    return {
        "delta_sharpe": delta,
        "delta_sharpe_ci95": [float(lower), float(upper)],
        "base_dd": base_dd,
        "candidate_dd": candidate_dd,
        "incremental_pass": bool(delta >= 0.1 and candidate_dd <= base_dd + 0.02 and lower > 0),
        "runs": runs,
        "seed": seed,
        "block_days": block_days,
        "days": len(x),
        "note": "Gate incremental; no reemplaza gates absolutos ni costos de API.",
    }
