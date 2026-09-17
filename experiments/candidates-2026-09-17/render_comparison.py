"""Regenera el gráfico comparativo desde las curvas registradas, sin nuevos backtests."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "runs"
SERIES = [
    ("WF-0014", "Referencia", "#202f46", "-"),
    ("WF-0012", "Donchian A", "#0072B2", "-"),
    ("WF-0013", "Donchian B (solo histórico)", "#0072B2", "--"),
    ("WF-0010", "Retrocesos A", "#D55E00", "-"),
    ("WF-0011", "Retrocesos B (solo histórico)", "#D55E00", "--"),
]
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, height_ratios=[2, 1])
for run_id, label, color, style in SERIES:
    folder = next(RUNS.glob(f"{run_id}-*"))
    frame = pd.read_csv(folder / "equity.csv")
    dates = pd.to_datetime(frame["ts"], unit="ms", utc=True)
    equity = frame["equity"] / 10000 * 100
    drawdown = (equity / equity.cummax() - 1) * 100
    axes[0].plot(dates, equity, color=color, ls=style, lw=1.7, label=label)
    axes[1].plot(dates, drawdown, color=color, ls=style, lw=1.3)
axes[0].axhline(100, color="#666666", lw=0.7, alpha=0.5)
axes[0].set_ylabel("Capital normalizado (inicial = 100)")
axes[1].set_ylabel("Caída desde el máximo (%)")
axes[1].set_xlabel("Fecha UTC")
axes[1].xaxis.set_major_locator(mdates.YearLocator())
axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
for axis in axes:
    axis.grid(axis="y", color="#e3e6ea", linewidth=0.7)
axes[0].legend(loc="upper left", fontsize=10, frameon=False)
fig.suptitle(
    "Más operaciones no aseguraron mejores resultados",
    fontsize=18,
    fontweight="bold",
    x=0.09,
    ha="left",
)
fig.text(
    0.09,
    0.92,
    "Walk-forward fijo · agosto 2021–julio 2025 · comisión 0,10 % + deslizamiento 5 bps por lado",
    fontsize=11,
)
fig.text(
    0.09,
    0.015,
    "Fuente: WF-0010 a WF-0014 · curvas OOS encadenadas; "
    "cada ventana reinicia cartera y protecciones.\n"
    "Resultados históricos simulados; no son una curva continua ni una aprobación para operar.",
    fontsize=9,
    color="#505b6b",
)
fig.subplots_adjust(left=0.09, right=0.98, top=0.88, bottom=0.12, hspace=0.12)
fig.savefig(HERE / "comparison.png", dpi=160)
plt.close(fig)
