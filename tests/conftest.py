"""Fixtures compartidos: velas reales de 2023 (parquet commiteado) como `OhlcvArrays`."""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
import pytest

from tradingbot.data.store import frame_to_candles
from tradingbot.domain import Candle, Pair, Timeframe
from tradingbot.strategy import OhlcvArrays

OHLCV_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ohlcv"


def load_real_candles(symbol: str = "BTCUSDT") -> list[Candle]:
    frame = pq.read_table(OHLCV_FIXTURES / f"{symbol}-4h-2023.parquet").to_pandas()
    return frame_to_candles(frame, Pair.parse(symbol), Timeframe.H4)


@pytest.fixture(scope="session")
def btc_2023() -> OhlcvArrays:
    return OhlcvArrays.from_candles(load_real_candles("BTCUSDT"))


@pytest.fixture(scope="session")
def eth_2023() -> OhlcvArrays:
    return OhlcvArrays.from_candles(load_real_candles("ETHUSDT"))
