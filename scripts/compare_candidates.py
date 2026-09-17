"""Ejecuta el protocolo congelado mediante CLI; nunca abre el holdout ni lanza paper.

Uso: uv run python scripts/compare_candidates.py [--dry-run]
Las corridas largas se ejecutan en background. Exige revisión git limpia para trazabilidad.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def commands() -> list[list[str]]:
    cli = str(Path(sys.executable).with_name("tradingbot"))
    result: list[list[str]] = []
    for strategy in ("pullback_rsi", "donchian"):
        for profile in ("a", "b"):
            config = f"configs/candidates/{strategy}-{profile}.yaml"
            label = f"candidates-{strategy}-{profile}"
            result.append([cli, "backtest", "--config", config, "--label", label])
            result.append(
                [
                    cli,
                    "walkforward",
                    "--config",
                    config,
                    "--fixed",
                    "--plateau",
                    "--is-months",
                    "24",
                    "--oos-months",
                    "6",
                    "--seed",
                    "42",
                    "--label",
                    label,
                ]
            )
            for bps in (10, 20):
                result.append(
                    [
                        cli,
                        "backtest",
                        "--config",
                        config,
                        "--set",
                        f"execution.slippage_bps={bps}",
                        "--label",
                        f"{label}-cost-{bps}",
                    ]
                )
    result.append(
        [
            cli,
            "backtest",
            "--config",
            "configs/regime-bh.yaml",
            "--from",
            "2019-08-01",
            "--to",
            "2025-09-01",
            "--label",
            "candidates-reference",
        ]
    )
    result.append(
        [
            cli,
            "walkforward",
            "--config",
            "configs/regime-bh.yaml",
            "--fixed",
            "--from",
            "2019-08-01",
            "--to",
            "2025-09-01",
            "--is-months",
            "24",
            "--oos-months",
            "6",
            "--seed",
            "42",
            "--label",
            "candidates-reference",
        ]
    )
    for strategy in ("pullback_rsi", "donchian"):
        for profile in ("a", "b"):
            for bps in (10, 20):
                result.append(
                    [
                        cli,
                        "walkforward",
                        "--config",
                        f"configs/candidates/{strategy}-{profile}.yaml",
                        "--fixed",
                        "--plateau",
                        "--is-months",
                        "24",
                        "--oos-months",
                        "6",
                        "--seed",
                        "42",
                        "--set",
                        f"execution.slippage_bps={bps}",
                        "--label",
                        f"candidates-{strategy}-{profile}-cost-{bps}",
                    ]
                )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=normal",
            "--",
            ".",
            ":(exclude)experiments",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status.strip() and not args.dry_run:
        raise SystemExit(
            "Primero congelar código/configs en una revisión git limpia; no se ejecutó nada."
        )
    for command in commands():
        print(" ".join(command), flush=True)
        if not args.dry_run:
            subprocess.run(command, cwd=root, check=True)


if __name__ == "__main__":
    main()
