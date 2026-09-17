"""Etiquetas netas y trazabilidad de la información disponible por cierre."""

from __future__ import annotations

import pandas as pd

from tradingbot.features.market import feature_frame
from tradingbot.strategy.base import OhlcvArrays


def labeled_frame(
    series: OhlcvArrays, btc: OhlcvArrays, *, fee: float = 0.001, slippage: float = 0.0005
) -> pd.DataFrame:
    frame = feature_frame(series, btc)
    opens = pd.Series(series.open, index=frame.index)
    times = pd.Series(series.open_time, index=frame.index)
    frame["net_return"] = (
        opens.shift(-7) * (1 - slippage) * (1 - fee) ** 2 / (opens.shift(-1) * (1 + slippage)) - 1
    )
    frame["label_end_ts"] = times.shift(-7)
    continuous = pd.Series(True, index=frame.index)
    for lag in range(1, 8):
        continuous &= times.shift(-lag) == times + lag * series.timeframe.ms
    frame["label"] = (frame.net_return > 0).astype(int)
    frame["pair"] = series.pair.symbol
    frame = frame.loc[continuous].dropna().reset_index()
    frame["label_end_ts"] = frame.label_end_ts.astype("int64")
    return frame
