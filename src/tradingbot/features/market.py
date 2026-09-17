"""Misma transformación causal para entrenamiento y snapshots de inferencia."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradingbot.indicators.core import adx, atr, highest, rsi, sma
from tradingbot.strategy.base import OhlcvArrays

FEATURE_VERSION = "market-v1"
SYMBOLS = (
    "BTC/USDT",
    "ETH/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "ADA/USDT",
    "LTC/USDT",
    "LINK/USDT",
    "SOL/USDT",
)
FEATURES = (
    "ret1",
    "ret3",
    "ret6",
    "ret18",
    "rsi14",
    "atr_ratio",
    "adx14",
    "ema_distance",
    "channel_distance",
    "volume_ratio",
    "btc_ret6",
    "btc_ret30d",
    "btc_sma_distance",
    *(f"pair_{s.split('/')[0]}" for s in SYMBOLS),
)
DAY = 86_400_000


def feature_frame(series: OhlcvArrays, btc: OhlcvArrays) -> pd.DataFrame:
    """Una fila por cierre exclusivo; ningún valor futuro ni estado de cartera."""
    if series.timeframe.ms != 14_400_000 or btc.timeframe != series.timeframe:
        raise ValueError("features market-v1 exige 4h")
    if series.pair.symbol not in SYMBOLS:
        raise ValueError("símbolo fuera del universo congelado")
    ts = series.open_time + series.timeframe.ms
    close = pd.Series(series.close, index=ts)
    vol = atr(series.high, series.low, series.close, 14)
    upper = pd.Series(highest(series.high, 60)).shift(1).to_numpy()
    # EMA200 sembrada siempre en la misma ventana finita de1213 barras.
    # Así entrenamiento e inferencia no dependen de un prefijo oculto al paper.
    width, period = 1213, 200
    decay = 1 - 2 / (period + 1)
    weights = np.empty(width)
    weights[:period] = decay ** (width - period) / period
    weights[period:] = (1 - decay) * decay ** np.arange(width - period - 1, -1, -1)
    average = np.convolve(series.close, weights[::-1], mode="full")[: len(close)]
    average[: width - 1] = np.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        frame = pd.DataFrame(
            {
                **{f"ret{n}": close.pct_change(n, fill_method=None) for n in (1, 3, 6, 18)},
                "rsi14": rsi(series.close, 14),
                "atr_ratio": vol / series.close,
                "adx14": adx(series.high, series.low, series.close, 14),
                "ema_distance": (series.close - average) / vol,
                "channel_distance": (series.close - upper) / vol,
                "volume_ratio": series.volume / sma(series.volume, 20),
            },
            index=ts,
        )
    btc_close = pd.Series(btc.close, index=btc.open_time + btc.timeframe.ms)
    # Exactitud de timestamp: BTC ausente en un bar no se completa con un precio viejo.
    frame["btc_ret6"] = btc_close.pct_change(6, fill_method=None).reindex(ts)
    days = pd.DataFrame({"open_time": btc.open_time, "close": btc.close})
    days["day"] = days.open_time // DAY
    daily = days.groupby("day").agg(
        count=("close", "size"),
        first=("open_time", "min"),
        last=("open_time", "max"),
        close=("close", "last"),
    )
    complete = (
        (daily["count"] == 6)
        & (daily["first"] == daily.index * DAY)
        & (daily["last"] == (daily.index + 1) * DAY - btc.timeframe.ms)
    )
    daily.loc[~complete, "close"] = np.nan
    daily = daily.reindex(range(int(daily.index.min()), int(daily.index.max()) + 1))
    daily.index = (daily.index + 1) * DAY
    values = pd.DataFrame(
        {
            "btc_ret30d": daily.close.pct_change(30, fill_method=None),
            "btc_sma_distance": daily.close / daily.close.rolling(200, min_periods=200).mean() - 1,
        }
    )
    # ffill del índice asof, no de los valores: un día incompleto sigue siendo inválido.
    values = values.reindex(ts, method="ffill")
    frame["btc_ret30d"] = values.btc_ret30d
    frame["btc_sma_distance"] = values.btc_sma_distance
    for symbol in SYMBOLS:
        frame[f"pair_{symbol.split('/')[0]}"] = float(series.pair.symbol == symbol)
    frame.index.name = "signal_ts"
    return frame.loc[:, list(FEATURES)].replace([np.inf, -np.inf], np.nan)
