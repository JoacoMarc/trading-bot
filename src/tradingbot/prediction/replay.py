"""Replay temporal con hash congelado y cobertura independiente de las oportunidades."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbot.domain import Pair, Signal
from tradingbot.prediction.base import EntryDecision
from tradingbot.research.models import digest
from tradingbot.strategy.base import StrategyContext


class ReplayFilter:
    def __init__(self, path: Path, expected_hash: str, threshold: float) -> None:
        self.threshold = threshold
        manifest = json.loads(path.read_text())
        if (
            manifest["manifest_hash"] != expected_hash
            or digest({k: v for k, v in manifest.items() if k != "manifest_hash"}) != expected_hash
        ):
            raise ValueError("hash del manifest de predicciones inválido")
        parquet = path.parent / "predictions.parquet"
        if hashlib.sha256(parquet.read_bytes()).hexdigest() != manifest["predictions_sha256"]:
            raise ValueError("predicciones alteradas")
        rows = pd.read_parquet(parquet)
        if rows.duplicated(["pair", "signal_ts"]).any():
            raise ValueError("predicciones duplicadas")
        self.models = {m["model_hash"]: m for m in manifest["models"]}
        if len(self.models) != len(manifest["models"]):
            raise ValueError("modelos duplicados")
        self.rows: dict[tuple[str, int], dict[str, Any]] = {}
        for record in rows.to_dict("records"):
            row = {str(k): v for k, v in record.items()}
            model = self.models.get(row["model_hash"])
            if (
                model is None
                or not math.isfinite(row["probability"])
                or not 0 <= row["probability"] <= 1
            ):
                raise ValueError("predicción inválida")
            if (
                row["available_at"] != model["available_at"]
                or row["expires_at"] != model["expires_at"]
            ):
                raise ValueError("disponibilidad de predicción inconsistente")
            if not model["available_at"] <= row["signal_ts"] < model["expires_at"]:
                raise ValueError("predicción fuera de vigencia")
            if (
                model["fit_label_end_max"] >= model["calibration_cut"]
                or model["calibration_label_end_max"] >= model["cut"]
                or model["available_at"] < model["cut"] + 3_600_000
            ):
                raise ValueError("modelo con fuga temporal")
            self.rows[row["pair"], row["signal_ts"]] = row
        coverage_path = path.parent / "coverage.parquet"
        if hashlib.sha256(coverage_path.read_bytes()).hexdigest() != manifest["coverage_sha256"]:
            raise ValueError("cobertura alterada")
        coverage_rows = pd.read_parquet(coverage_path)
        if coverage_rows.duplicated(["pair", "signal_ts"]).any():
            raise ValueError("cobertura duplicada")
        self.expected: dict[tuple[str, int], str] = {}
        for coverage_row in coverage_rows.itertuples(index=False):
            key = (str(coverage_row.pair), int(str(coverage_row.signal_ts)))
            reason = str(coverage_row.reason)
            if reason not in {"ok", "features_invalid", "model_missing"}:
                raise ValueError("motivo de cobertura inválido")
            if (reason == "ok") != (key in self.rows):
                raise ValueError("cobertura y predicciones inconsistentes")
            self.expected[key] = reason
        self.coverage: Counter[str] = Counter()
        self.missing_model_years: set[int] = set()

    def observe(self, contexts: Mapping[Pair, StrategyContext], signal_ts: int) -> None:
        available = any(
            m["available_at"] <= signal_ts < m["expires_at"] for m in self.models.values()
        )
        month = pd.Timestamp(signal_ts, unit="ms", tz="UTC").strftime("%Y-%m")
        for pair in contexts:
            reason = self.expected.get((pair.symbol, signal_ts), "coverage_missing")
            if not available:
                reason = "model_missing"
            self.coverage[f"{month}|{pair.symbol}|{reason}"] += 1
            if reason in {"model_missing", "coverage_missing"}:
                self.missing_model_years.add(int(month[:4]))

    def evaluate(self, signal: Signal, signal_ts: int) -> EntryDecision:
        row = self.rows.get((signal.pair.symbol, signal_ts))
        if row is None:
            return EntryDecision(False, "prediction_missing")
        valid = row["available_at"] <= signal_ts < row["expires_at"]
        return EntryDecision(
            valid and row["probability"] >= self.threshold,
            "prediction_accept"
            if valid and row["probability"] >= self.threshold
            else "prediction_veto",
            f"{row['model_hash']}:{signal.pair.symbol}:{signal_ts}",
        )
