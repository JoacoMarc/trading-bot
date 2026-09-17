"""Receta fija mensual y artefactos JSON; no se deserializa código pickle."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from tradingbot.features.market import FEATURE_VERSION, FEATURES

ModelKind = Literal["logistic", "lightgbm"]
HOUR = 3_600_000


def stamp(value: pd.Timestamp) -> int:
    return int(value.timestamp() * 1000)


def sigmoid(values: NDArray[np.float64]) -> NDArray[np.float64]:
    return np.asarray(1 / (1 + np.exp(-np.clip(values, -700, 700))), dtype=np.float64)


def digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class TemporalSplit:
    fit: pd.DataFrame
    calibration: pd.DataFrame
    cut: int
    calibration_cut: int


def temporal_split(frame: pd.DataFrame, cut: pd.Timestamp, months: int = 24) -> TemporalSplit:
    start = stamp(cut - pd.DateOffset(months=months))
    boundary = stamp(cut - pd.DateOffset(months=3))
    end = stamp(cut)
    fit = frame.loc[
        (frame.signal_ts >= start) & (frame.signal_ts < boundary) & (frame.label_end_ts < boundary)
    ]
    calibration = frame.loc[
        (frame.signal_ts >= boundary) & (frame.signal_ts < end) & (frame.label_end_ts < end)
    ]
    return TemporalSplit(fit, calibration, end, boundary)


def raw_predict(model: dict[str, Any], frame: pd.DataFrame) -> NDArray[np.float64]:
    values = frame.loc[:, list(FEATURES)].to_numpy(dtype=float)
    if model["kind"] == "logistic":
        normalized = (values - np.asarray(model["mean"])) / np.asarray(model["scale"])
        return np.asarray(
            normalized @ np.asarray(model["coef"]) + model["intercept"], dtype=np.float64
        )
    if model["kind"] != "lightgbm":
        raise ValueError("tipo de modelo desconocido")
    import lightgbm as lgb

    booster = lgb.Booster(model_str=model["booster"])
    return np.asarray(booster.predict(values, raw_score=True, num_threads=2), dtype=np.float64)


def predict(model: dict[str, Any], frame: pd.DataFrame) -> NDArray[np.float64]:
    if model["feature_version"] != FEATURE_VERSION or model["features"] != list(FEATURES):
        raise ValueError("schema de features incompatible")
    return sigmoid(
        raw_predict(model, frame) * model["calibration_coef"] + model["calibration_intercept"]
    )


def train_month(
    frame: pd.DataFrame,
    cut: pd.Timestamp,
    kind: ModelKind,
    *,
    source_start: int,
    data_hash: str,
    seed: int = 42,
    months: int = 24,
) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    split = temporal_split(frame, cut, months)
    if source_start > stamp(cut - pd.DateOffset(months=months)):
        raise ValueError("historia menor a la ventana de entrenamiento")
    if len(split.fit) < 1000 or len(split.calibration) < 200:
        raise ValueError("muestras insuficientes")
    if split.fit.label.nunique() != 2 or split.calibration.label.nunique() != 2:
        raise ValueError("se requieren ambas clases en fit y calibración")
    x = split.fit.loc[:, list(FEATURES)].to_numpy(dtype=float)
    y = split.fit.label.to_numpy()
    model: dict[str, Any] = {
        "versions": {
            name: version(name) for name in ("numpy", "pandas", "scikit-learn", "lightgbm")
        },
        "lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        "kind": kind,
        "feature_version": FEATURE_VERSION,
        "features": list(FEATURES),
        "cut": split.cut,
        "available_at": split.cut + HOUR,
        "expires_at": stamp(cut + pd.DateOffset(months=1)) + HOUR,
        "fit_start": stamp(cut - pd.DateOffset(months=months)),
        "calibration_cut": split.calibration_cut,
        "fit_label_end_max": int(split.fit.label_end_ts.max()),
        "calibration_label_end_max": int(split.calibration.label_end_ts.max()),
        "fit_rows": len(split.fit),
        "calibration_rows": len(split.calibration),
        "data_hash": data_hash,
        "seed": seed,
        "months": months,
    }
    if kind == "logistic":
        scaler = StandardScaler().fit(x)
        estimator = LogisticRegression(C=1, max_iter=1000, random_state=seed).fit(
            scaler.transform(x), y
        )
        model.update(
            mean=scaler.mean_.tolist(),
            scale=scaler.scale_.tolist(),
            coef=estimator.coef_[0].tolist(),
            intercept=float(estimator.intercept_[0]),
        )
    else:
        import lightgbm as lgb

        estimator = lgb.LGBMClassifier(
            n_estimators=100,
            num_leaves=15,
            max_depth=5,
            learning_rate=0.05,
            min_child_samples=100,
            reg_lambda=1,
            n_jobs=2,
            random_state=seed,
            deterministic=True,
            force_col_wise=True,
            verbosity=-1,
        ).fit(x, y)
        model["booster"] = estimator.booster_.model_to_string()
    model["estimator_params"] = estimator.get_params()
    raw = raw_predict(model, split.calibration).reshape(-1, 1)
    calibrator = LogisticRegression(C=1, max_iter=1000, random_state=seed).fit(
        raw, split.calibration.label.to_numpy()
    )
    model["calibrator_params"] = calibrator.get_params()
    model.update(
        calibration_coef=float(calibrator.coef_[0][0]),
        calibration_intercept=float(calibrator.intercept_[0]),
    )
    model["model_hash"] = digest(model)
    return model


def validate_model(model: dict[str, Any], now: int, *, published_at: int | None = None) -> None:
    original = {k: v for k, v in model.items() if k != "model_hash"}
    if digest(original) != model["model_hash"]:
        raise ValueError("hash de modelo inválido")
    available = max(model["available_at"], published_at or 0)
    if not available <= now < model["expires_at"]:
        raise ValueError("modelo futuro o vencido")
    if (
        model["fit_label_end_max"] >= model["calibration_cut"]
        or model["calibration_label_end_max"] >= model["cut"]
    ):
        raise ValueError("artefacto sin purga temporal")
