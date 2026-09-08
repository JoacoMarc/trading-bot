from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from tradingbot.config import DEFAULT_UNIVERSE, BotConfig, DataConfig
from tradingbot.domain import Pair, Timeframe


def test_defaults_cover_the_v1_universe() -> None:
    cfg = DataConfig()
    assert len(cfg.universe) == 8
    assert cfg.universe == DEFAULT_UNIVERSE
    assert cfg.universe[0] == Pair.parse("ADA/USDT")  # ordenado alfabéticamente
    assert cfg.timeframes == (Timeframe.H1, Timeframe.H4)
    assert cfg.since == date(2019, 1, 1)
    assert cfg.gaps_file == Path("configs") / "binance_gaps.json"


def test_timeframes_parse_sort_and_reject_duplicates() -> None:
    assert DataConfig(timeframes="4h 1h").timeframes == (Timeframe.H1, Timeframe.H4)
    assert DataConfig(timeframes=["1d"]).timeframes == (Timeframe.D1,)
    with pytest.raises(ValidationError, match="repetido"):
        DataConfig(timeframes=["1h", "1h"])
    with pytest.raises(ValidationError):
        DataConfig(timeframes=[])


def test_data_config_round_trips_through_public_dump() -> None:
    cfg = BotConfig.load(
        overrides={
            "strategy": {"name": "ema_trend", "pairs": ["BTC/USDT"]},
            "data": {"timeframes": ["4h"]},
        },
        env_file=None,
    )
    dumped = cfg.public_dump()
    assert dumped["data"]["timeframes"] == ["4h"]
    reloaded = BotConfig.load(overrides=dumped, env_file=None)
    assert reloaded.data == cfg.data
