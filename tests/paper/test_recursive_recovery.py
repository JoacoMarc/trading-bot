"""Checkpoint recursivo atómico y recuperación del feed real del paper."""

from pathlib import Path
from typing import Any

import pytest

from tests.factories import BTC, ETH
from tests.paper.test_runner import FakePaperExchange, paper_config, rising_days
from tradingbot.config.models import StrategyConfig
from tradingbot.domain import Bar
from tradingbot.paper.runner import ENGINE_STATE_KEY, INDICATOR_STATE_KEY, build_paper_session
from tradingbot.persistence import SqliteStore


def setup_session(tmp_path: Path) -> tuple[Any, FakePaperExchange, Any]:
    candles = rising_days(207)
    config = paper_config(tmp_path).model_copy(
        update={"strategy": StrategyConfig(name="supertrend", pairs=[BTC, ETH], timeframe="4h")}
    )
    exchange = FakePaperExchange(
        {BTC: candles, ETH: [c.model_copy(update={"pair": ETH}) for c in candles]},
        now_ms=candles[1213].open_time + 300_000,
    )
    exchange.last = {BTC: "302", ETH: "302"}
    return config, exchange, build_paper_session(config, exchange, sleep=exchange.sleep)


def test_restart_catches_up_pair_missing_at_global_cursor(tmp_path: Path) -> None:
    config, exchange, session = setup_session(tmp_path)
    checkpoint = session.engine.indicator_checkpoint()
    next_ts = checkpoint[BTC.symbol]["last_time"] + config.strategy.timeframe.ms
    btc = next(c for c in exchange.candles[BTC] if c.open_time == next_ts)
    # BTC avanza; ETH no publicó esa vela. Al reiniciar sí está disponible en el exchange.
    exchange.now += config.strategy.timeframe.ms
    session.process(Bar.from_candles((btc,)))
    assert session.engine.indicator_checkpoint()[ETH.symbol]["last_time"] < next_ts
    session.store.close()
    resumed = build_paper_session(config, exchange, sleep=exchange.sleep)
    assert resumed.engine.indicator_checkpoint()[ETH.symbol]["last_time"] == next_ts
    assert resumed.engine.state().last_bar_open_time == next_ts
    assert resumed.bars_processed == 0  # catchup de indicadores no ejecuta órdenes
    resumed.store.close()


async def test_shutdown_before_first_bar_preserves_seed_and_replays(tmp_path: Path) -> None:
    config, exchange, session = setup_session(tmp_path)
    before = session.engine.indicator_checkpoint()
    session.request_stop()
    await session.run(install_signals=False)
    exchange.now += 3 * config.strategy.timeframe.ms
    resumed = build_paper_session(config, exchange, sleep=exchange.sleep)
    assert resumed.engine.state().last_bar_open_time is None
    assert resumed.engine.indicator_checkpoint() == before
    assert resumed.feed.replay_pending >= 3
    resumed.store.close()


def test_checkpoint_and_engine_rollback_together(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, exchange, session = setup_session(tmp_path)
    session.persist()
    before = session.store.load_state(INDICATOR_STATE_KEY)
    engine_before = session.store.load_state(ENGINE_STATE_KEY)
    saved = session.store.save_state

    def fail_after_checkpoint(key: str, value: dict[str, Any]) -> None:
        saved(key, value)
        if key == INDICATOR_STATE_KEY:
            raise RuntimeError("corte después de checkpoint")

    monkeypatch.setattr(session.store, "save_state", fail_after_checkpoint)
    next_ts = before[BTC.symbol]["last_time"] + config.strategy.timeframe.ms
    bar = Bar.from_candles(
        tuple(next(c for c in exchange.candles[p] if c.open_time == next_ts) for p in (BTC, ETH))
    )
    with pytest.raises(RuntimeError, match="checkpoint"):
        session.process(bar)
    session.store.close()
    store = SqliteStore(config.db_path)
    assert store.load_state(INDICATOR_STATE_KEY) == before
    assert store.load_state(ENGINE_STATE_KEY) == engine_before
    store.close()
    resumed = build_paper_session(config, exchange, sleep=exchange.sleep)
    assert resumed.engine.indicator_checkpoint() == before
    resumed.store.close()
