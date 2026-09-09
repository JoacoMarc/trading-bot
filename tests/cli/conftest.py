"""Fixture compartido de la CLI: store temporal con los fixtures sintéticos de 2023."""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
import pytest

from tradingbot.data.store import ParquetStore, frame_to_candles
from tradingbot.domain import Pair, Timeframe

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ohlcv"

CONFIG_TEMPLATE = """
mode: backtest
strategy:
  name: ema_trend
  timeframe: 4h
  pairs: [BTC/USDT, ETH/USDT]
  params:
    ema_fast: 5
    ema_slow: 12
    ema_regime: 30
    adx_period: 5
    adx_threshold: 15
    atr_period: 5
    warmup_multiplier: 5
risk:
  max_positions: 2
backtest:
  initial_cash: 10000
data:
  data_dir: {data_dir}
"""


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("bt")
    data_dir = root / "data"
    store = ParquetStore(data_dir)
    for symbol in ("BTCUSDT", "ETHUSDT"):
        frame = pq.read_table(FIXTURES / f"synthetic-{symbol}-4h-2023.parquet").to_pandas()
        store.write_candles(
            Pair.parse(symbol),
            Timeframe.H4,
            frame_to_candles(frame, Pair.parse(symbol), Timeframe.H4),
        )
    config = root / "backtest.yaml"
    config.write_text(CONFIG_TEMPLATE.format(data_dir=data_dir.as_posix()), encoding="utf-8")
    return {"root": root, "config": config, "experiments": root / "experiments"}
