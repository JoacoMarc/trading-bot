"""Cobertura explícita, integridad de artefactos y paridad replay/inferencia local."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from tests.factories import BTC, ETH, make_series
from tests.research.test_models import training_frame

from tradingbot.cli.research_commands import read_dataset
from tradingbot.domain import Signal, SignalAction
from tradingbot.features.market import feature_frame
from tradingbot.prediction.local import LocalFilter
from tradingbot.prediction.replay import ReplayFilter
from tradingbot.research.models import digest, predict, stamp, train_month
from tradingbot.strategy.base import OhlcvArrays, StrategyContext


def fixture(tmp_path: Path) -> tuple[ReplayFilter, LocalFilter, StrategyContext, Signal, int]:
    cut = pd.Timestamp("2022-01-01", tz="UTC")
    model = train_month(
        training_frame(),
        cut,
        "logistic",
        source_start=stamp(cut - pd.DateOffset(months=24)),
        data_hash="fixture",
    )
    arrays = OhlcvArrays.from_candles(make_series(start=1_609_459_200_000, n=2202))
    ctx = StrategyContext(ohlcv=arrays, indicators={}, index=len(arrays) - 1)
    ts = ctx.candle.close_time + 1
    probability = float(predict(model, feature_frame(arrays, arrays).iloc[[-1]])[0])
    pd.DataFrame(
        [
            {
                "pair": BTC.symbol,
                "signal_ts": ts,
                "probability": probability,
                "available_at": model["available_at"],
                "expires_at": model["expires_at"],
                "model_hash": model["model_hash"],
            }
        ]
    ).to_parquet(tmp_path / "predictions.parquet")
    pd.DataFrame(
        [
            {"pair": BTC.symbol, "signal_ts": ts, "reason": "ok"},
            {"pair": ETH.symbol, "signal_ts": ts, "reason": "features_invalid"},
        ]
    ).to_parquet(tmp_path / "coverage.parquet")
    manifest: dict[str, Any] = {
        "models": [model],
        "predictions_sha256": hashlib.sha256(
            (tmp_path / "predictions.parquet").read_bytes()
        ).hexdigest(),
        "coverage_sha256": hashlib.sha256((tmp_path / "coverage.parquet").read_bytes()).hexdigest(),
    }
    manifest["manifest_hash"] = digest(manifest)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "publication.json").write_text(
        json.dumps({"model": model, "published_at": model["available_at"]})
    )
    replay = ReplayFilter(tmp_path / "manifest.json", manifest["manifest_hash"], 0.55)
    local = LocalFilter(tmp_path / "publication.json", 0.55)
    signal = Signal(
        action=SignalAction.ENTER_LONG, pair=BTC, open_time=ctx.open_time, stop_price=ctx.candle.low
    )
    return replay, local, ctx, signal, ts


def test_local_and_replay_agree_and_truncated_coverage_cannot_pass(tmp_path: Path) -> None:
    replay, local, ctx, signal, ts = fixture(tmp_path)
    for provider in (replay, local):
        provider.observe({BTC: ctx}, ts)
    assert replay.evaluate(signal, ts) == local.evaluate(signal, ts)
    assert not replay.missing_model_years
    replay.observe({BTC: ctx}, ts + 14_400_000)  # modelo vigente; archivo truncado
    assert replay.missing_model_years == {2022}
    assert any(key.endswith("coverage_missing") for key in replay.coverage)
    assert not replay.evaluate(signal, ts + 14_400_000).accepted
    replay.observe({BTC: ctx}, ts + 40 * 86_400_000)  # mes sin modelo, aunque no haya compras
    assert any(key.endswith("model_missing") for key in replay.coverage)


def test_replay_rejects_modified_predictions(tmp_path: Path) -> None:
    fixture(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    with (tmp_path / "predictions.parquet").open("ab") as handle:
        handle.write(b"changed")
    with pytest.raises(ValueError, match="alteradas"):
        ReplayFilter(tmp_path / "manifest.json", manifest["manifest_hash"], 0.55)


def test_old_feature_schema_cannot_be_relabelled(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text(json.dumps({"feature_version": "old"}))
    with pytest.raises(ValueError, match="schema"):
        read_dataset(tmp_path)
