"""Monte Carlo por bootstrap de trades (ADR-0008).

Re-muestrea con reemplazo los PnL en quote de los trades (n por corrida), arma la equity como
cash inicial + PnL acumulado y mide el max drawdown de cada camino. Estresa la dependencia de
pocos trades grandes; no cambia la estrategia ni el orden temporal de los precios.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

import numpy as np


@dataclass(frozen=True, slots=True)
class MonteCarloResult:
    runs: int
    trades: int
    seed: int
    dd_p50: float
    dd_p95: float
    dd_p99: float
    return_p05: float
    return_p50: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "runs": self.runs,
            "trades": self.trades,
            "seed": self.seed,
            "dd_p50": self.dd_p50,
            "dd_p95": self.dd_p95,
            "dd_p99": self.dd_p99,
            "return_p05": self.return_p05,
            "return_p50": self.return_p50,
        }


def bootstrap_trades(
    pnls: Sequence[Decimal],
    initial_cash: Decimal,
    *,
    runs: int = 5_000,
    seed: int = 42,
) -> MonteCarloResult:
    """Percentiles del max DD y del retorno final sobre `runs` remuestreos con reemplazo."""
    if runs <= 0:
        msg = f"runs debe ser positivo, recibido {runs}"
        raise ValueError(msg)
    n = len(pnls)
    if n == 0:
        return MonteCarloResult(runs, 0, seed, 0.0, 0.0, 0.0, 0.0, 0.0)
    pnl = np.asarray([float(p) for p in pnls], dtype=np.float64)
    initial = float(initial_cash)
    rng = np.random.default_rng(seed)
    samples = pnl[rng.integers(0, n, size=(runs, n))]
    equity = initial + np.cumsum(samples, axis=1)
    equity = np.concatenate([np.full((runs, 1), initial), equity], axis=1)
    peaks = np.maximum.accumulate(equity, axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        # PnL aditivo: la equity puede irse a cero o negativa; un DD nunca supera el 100 %.
        drawdowns = np.where(peaks > 0, np.minimum((peaks - equity) / peaks, 1.0), 1.0)
    max_dd = drawdowns.max(axis=1)
    returns = equity[:, -1] / initial - 1.0
    return MonteCarloResult(
        runs=runs,
        trades=n,
        seed=seed,
        dd_p50=float(np.percentile(max_dd, 50)),
        dd_p95=float(np.percentile(max_dd, 95)),
        dd_p99=float(np.percentile(max_dd, 99)),
        return_p05=float(np.percentile(returns, 5)),
        return_p50=float(np.percentile(returns, 50)),
    )
