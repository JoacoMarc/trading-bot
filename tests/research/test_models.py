"""Causalidad, costos, calibración temporal y artefactos sin deserializar código."""

import numpy as np
import pandas as pd
import pytest
from tests.factories import make_series

from tradingbot.features.market import FEATURES, feature_frame
from tradingbot.research.dataset import labeled_frame
from tradingbot.research.models import (
    ModelKind,
    predict,
    stamp,
    temporal_split,
    train_month,
    validate_model,
)
from tradingbot.strategy.base import OhlcvArrays


def test_features_batch_prefix_and_rolling_match_without_future() -> None:
    arrays = OhlcvArrays.from_candles(make_series(n=1700, start=1_704_067_200_000))
    full = feature_frame(arrays, arrays)
    for n in (1320, 1451, 1690):
        prefix = arrays.slice(0, n)
        window = arrays.slice(n - 1213, n)
        np.testing.assert_allclose(
            feature_frame(prefix, prefix).iloc[-1], full.iloc[n - 1], rtol=1e-8
        )
        np.testing.assert_allclose(
            feature_frame(window, window).iloc[-1], full.iloc[n - 1], rtol=1e-10
        )
    # Todavía no existen 200 días cerrados al cierre intradiario de la jornada200.
    assert np.isnan(full.iloc[1198].btc_sma_distance)
    assert np.isfinite(full.iloc[1199].btc_sma_distance)


def test_label_has_correct_24h_costs_and_excludes_gaps() -> None:
    arrays = OhlcvArrays.from_candles(make_series(n=1600))
    frame = labeled_frame(arrays, arrays)
    row = frame.iloc[0]
    i = list(arrays.open_time + arrays.timeframe.ms).index(row.signal_ts)
    expected = arrays.open[i + 7] * 0.9995 * 0.999**2 / (arrays.open[i + 1] * 1.0005) - 1
    assert row.net_return == pytest.approx(expected)
    assert row.label_end_ts - row.signal_ts == 86_400_000
    missing = OhlcvArrays.from_candles(make_series(n=1600, skip=frozenset({1500})))
    observed = labeled_frame(missing, missing)
    assert not observed.signal_ts.between(
        arrays.open_time[1493] + arrays.timeframe.ms, arrays.open_time[1499] + arrays.timeframe.ms
    ).any()
    assert set(FEATURES).isdisjoint({"label", "label_end_ts", "net_return"})


def training_frame() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2020-01-01", "2022-02-01", freq="4h", tz="UTC")
    data = pd.DataFrame(rng.normal(size=(len(dates), len(FEATURES))), columns=FEATURES)
    data["signal_ts"] = dates.as_unit("ms").astype("int64")
    data["label_end_ts"] = data.signal_ts + 86_400_000
    data["label"] = (data.ret1 + data.ret6 > 0).astype(int)
    return data


@pytest.mark.parametrize("kind", ["logistic", "lightgbm"])
def test_models_purge_future_and_are_reproducible(kind: ModelKind) -> None:
    frame = training_frame()
    cut = pd.Timestamp("2022-01-01", tz="UTC")
    split = temporal_split(frame, cut)
    assert split.fit.label_end_ts.max() < split.calibration_cut
    assert split.calibration.label_end_ts.max() < split.cut
    model = train_month(
        frame, cut, kind, source_start=stamp(cut - pd.DateOffset(months=24)), data_hash="fixture"
    )
    altered = frame.copy()
    altered.loc[altered.label_end_ts >= split.cut, "label"] = 1
    repeat = train_month(
        altered, cut, kind, source_start=stamp(cut - pd.DateOffset(months=24)), data_hash="fixture"
    )
    assert repeat == model
    values = predict(model, frame.tail(10))
    assert np.isfinite(values).all()
    assert ((values >= 0) & (values <= 1)).all()
    validate_model(model, model["available_at"])
    for now in (model["available_at"] - 1, model["expires_at"]):
        with pytest.raises(ValueError, match="futuro o vencido"):
            validate_model(model, now)
    with pytest.raises(ValueError, match="hash"):
        validate_model({**model, "calibration_coef": 9}, model["available_at"])
    with pytest.raises(ValueError, match="futuro o vencido"):
        validate_model(model, model["available_at"], published_at=model["available_at"] + 1)


def test_incremental_gate_uses_intraday_drawdown() -> None:
    from tradingbot.research.comparison import paired_comparison

    dates = pd.date_range("2020-01-01", periods=365 * 6, freq="4h", tz="UTC")
    base = pd.DataFrame(
        {"ts": dates.as_unit("ms").astype("int64"), "equity": np.linspace(10000, 12000, len(dates))}
    )
    candidate = base.copy()
    candidate.loc[100, "equity"] = 5000
    result = paired_comparison(base, candidate, runs=100)
    assert result["candidate_dd"] > 0.5
    assert not result["incremental_pass"]
