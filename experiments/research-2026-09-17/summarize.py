"""Agrega artefactos existentes; no entrena, simula ni consulta APIs."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "runs"


def run(number: int, kind: str = "WF") -> Path:
    return next(RUNS.glob(f"{kind}-{number:04d}-*"))


rows = []
for number in range(23, 53):
    path = run(number)
    payload = json.loads((path / "metrics.json").read_text())
    metrics = payload["metrics"]
    curve = pd.read_csv(path / "equity.csv")
    daily = (
        pd.Series(curve.equity.to_numpy(), index=pd.to_datetime(curve.ts, unit="ms", utc=True))
        .resample("D")
        .last()
        .pct_change(fill_method=None)
        .dropna()
    )
    trades = pd.read_csv(path / "trades.csv")
    rows.append(
        {
            "run": path.name,
            **metrics,
            "volatility_annualized": float(daily.std(ddof=1) * np.sqrt(365)),
            "closes_per_month": metrics["trades"] / 48,
            "active_months": pd.to_datetime(trades.exit_time).dt.strftime("%Y-%m").nunique(),
            "gate": payload["meta"]["extra"]["gate_verdict"],
            "plateau_pass_rate": payload["meta"]["extra"]["plateau"]["pass_rate"],
            "mc_dd_p95": payload["meta"]["extra"]["montecarlo"]["dd_p95"],
        }
    )
pd.DataFrame(rows).drop(columns=["exits"]).to_csv(HERE / "oos-summary.csv", index=False)

dataset = pd.read_parquet(run(1, "RES") / "dataset.parquet")
start = pd.Timestamp("2021-08-01", tz="UTC").value // 1_000_000
end = pd.Timestamp("2025-08-01", tz="UTC").value // 1_000_000
bins = np.linspace(0, 1, 21)
bin_rows, scores = [], []
fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True)
for number, name, color in [(3, "Logística", "#0072B2"), (5, "LightGBM", "#D55E00")]:
    predicted = pd.read_parquet(run(number, "RES") / "predictions.parquet")
    sample = predicted.merge(dataset, on=["pair", "signal_ts"], validate="one_to_one")
    sample = sample[(sample.signal_ts >= start) & (sample.signal_ts < end)]
    for column, (group, subset) in enumerate(
        [
            ("Todas las velas elegibles", sample),
            ("Rupturas previas a filtros de cartera", sample[sample.channel_distance > 0]),
        ]
    ):
        grouped = subset.groupby(
            pd.cut(subset.probability, bins, include_lowest=True), observed=True
        )
        reliability = grouped.agg(
            prediction=("probability", "mean"), observed=("label", "mean"), n=("label", "size")
        )
        for interval, row in reliability.iterrows():
            bin_rows.append({"model": name, "sample": group, "bin": str(interval), **row.to_dict()})
        axes[0, column].plot(
            reliability.prediction, reliability.observed, "o-", label=name, color=color
        )
        axes[1, column].hist(
            subset.probability, bins=bins, histtype="step", linewidth=2, label=name, color=color
        )
        scores.append(
            {
                "model": name,
                "sample": group,
                "rows": len(subset),
                "brier": float(((subset.probability - subset.label) ** 2).mean()),
                "log_loss": float(
                    -(
                        subset.label * np.log(subset.probability)
                        + (1 - subset.label) * np.log1p(-subset.probability)
                    ).mean()
                ),
                "accepted_at_055": int((subset.probability >= 0.55).sum()),
            }
        )
        axes[0, column].set_title(f"{group}\nn={len(subset):,}".replace(",", "."))
for column in range(2):
    axes[0, column].plot([0, 1], [0, 1], "--", color="gray", linewidth=1, label="Identidad")
    axes[0, column].set(ylabel="Frecuencia positiva observada", ylim=(0, 1))
    axes[0, column].yaxis.set_major_formatter(PercentFormatter(1))
    axes[1, column].set(
        ylabel="Filas por intervalo (escala log)", xlabel="Probabilidad predicha", yscale="log"
    )
    for row in range(2):
        ax = axes[row, column]
        ax.set_xlim(0, 1)
        ax.xaxis.set_major_formatter(PercentFormatter(1))
        ax.axvline(0.55, color="gray", alpha=0.4)
        ax.grid(alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(fontsize=8)
fig.suptitle("Calibración OOS: predicciones concentradas cerca de 50 %", fontsize=14)
fig.text(
    0.5,
    0.01,
    "2021-08 a 2025-08 exclusivo · bins de 5 pp · etiquetas solapadas, no independientes",
    ha="center",
    fontsize=9,
)
fig.tight_layout(rect=(0, 0.035, 1, 0.96))
fig.savefig(HERE / "calibration.png", dpi=160)
pd.DataFrame(bin_rows).to_csv(HERE / "calibration-bins.csv", index=False)
(HERE / "calibration-scores.json").write_text(json.dumps(scores, indent=2) + "\n")
