"""Sesión de paper (ADR-0011): arranque limpio, fills al open en formación, estado y reanudación."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

import pytest

from tests.data.test_live_feed import FakeSource
from tests.engine.fakes import MARKETS
from tests.factories import BTC, d
from tests.risk.test_market_filter import day_candles
from tradingbot.config.models import Mode
from tradingbot.config.settings import BotConfig
from tradingbot.domain import Candle, OrderStatus, Pair, Side
from tradingbot.domain.errors import ConfigError
from tradingbot.exchange.binance import MarketInfo
from tradingbot.paper import ENGINE_STATE_KEY, build_paper_session
from tradingbot.paper.runner import PENDING_DROPPED
from tradingbot.persistence import SqliteStore
from tradingbot.risk import ReasonCode

MS_PER_DAY = 86_400_000


class FakePaperExchange(FakeSource):
    def __init__(self, candles: dict[Pair, Sequence[Candle]], now_ms: int) -> None:
        super().__init__(candles, now_ms)
        self.last: dict[Pair, str] = {}

    def fetch_last_price(self, pair: Pair) -> Decimal:
        return d(self.last.get(pair, "0"))

    def load_markets(self, reload: bool = False) -> dict[Pair, MarketInfo]:
        return dict(MARKETS)


def paper_config(tmp_path: Path, **risk: object) -> BotConfig:
    return BotConfig(
        mode="paper",
        strategy={
            "name": "regime_bh",
            "timeframe": "4h",
            "pairs": ["BTC/USDT"],
            "params": {"sma_days": 3, "momentum_days": 2},
        },
        risk={
            "sizing_mode": "fraction",
            "position_fraction": "0.5",
            "max_positions": 1,
            "daily_loss_limit_pct": None,
            "max_drawdown_pct": None,
            "kill_switch_file": str(tmp_path / "logs" / "STOP"),
            **risk,
        },
        execution={"slippage_bps": 0},
        persistence={"db_dir": str(tmp_path / "db"), "logs_dir": str(tmp_path / "logs")},
        data={"data_dir": str(tmp_path / "data")},
    )


def rising_days(n: int) -> list[Candle]:
    return [c for day in range(n) for c in day_candles(day, str(100 + day))]


async def test_fresh_session_enters_at_forming_open_and_persists_state(tmp_path: Path) -> None:
    candles = rising_days(8)  # 48 velas; warmup de regime_bh(3, 2) = 30
    start_day5 = candles[30].open_time
    exchange = FakePaperExchange({BTC: candles}, now_ms=start_day5 + 300_000)
    exchange.last[BTC] = "105"
    config = paper_config(tmp_path)
    session = build_paper_session(config, exchange, sleep=exchange.sleep)
    assert not session.restored
    assert session.feed.replay_pending == 0

    processed = await session.run(max_bars=2, install_signals=False)
    assert processed == 2
    store = SqliteStore(config.db_path)
    fills = store.fills()
    assert [f.side for f in fills] == [Side.BUY]
    # Señal al cierre de la vela 30 (régimen encendido) -> fill al open de la vela 31, enseguida.
    assert fills[0].ref_price == candles[31].open
    assert fills[0].fill_ts >= candles[31].open_time
    assert fills[0].fill_ts < candles[31].open_time + 60_000
    positions = store.load_open_positions()
    assert len(positions) == 1
    assert positions[0].qty * fills[0].price == pytest.approx(d("5000"), rel=Decimal("0.01"))
    state = store.load_state(ENGINE_STATE_KEY)
    assert state is not None
    assert state["last_bar_open_time"] == candles[31].open_time
    assert state["bar_index"] == 1
    status = json.loads((tmp_path / "logs" / "status.json").read_text(encoding="utf-8"))
    assert status["phase"] == "detenido"
    assert status["positions"][0]["pair"] == "BTC/USDT"
    assert status["positions"][0]["stop_published"] is True
    assert status["stats"]["bars"] == 2
    assert status["timeframe_ms"] == 4 * 3_600_000
    assert Decimal(status["equity"]) > 0
    store.close()


async def test_restart_restores_position_replays_missed_bars_and_drops_pending(
    tmp_path: Path,
) -> None:
    candles = rising_days(10)
    exchange = FakePaperExchange({BTC: candles}, now_ms=candles[30].open_time + 300_000)
    exchange.last[BTC] = "105"
    config = paper_config(tmp_path)
    first = build_paper_session(config, exchange, sleep=exchange.sleep)
    await first.run(max_bars=2, install_signals=False)

    # Simular una orden pendiente huérfana y un proceso que murió 3 velas atrás.
    store = SqliteStore(config.db_path)
    orphan = store.orders()[0].model_copy(update={"status": OrderStatus.PENDING})
    store.save_order(orphan)
    store.close()
    exchange.now = candles[35].open_time + 300_000  # las velas 32, 33 y 34 cerraron sin proceso
    second = build_paper_session(config, exchange, sleep=exchange.sleep)
    assert second.restored
    assert second.engine.positions.get(BTC) is not None
    assert second.broker.get_stop(BTC) is not None  # stop re-publicado
    assert second.feed.replay_pending == 3
    processed = await second.run(max_bars=4, install_signals=False)  # 3 reposiciones + 1 en vivo
    assert processed == 4
    store = SqliteStore(config.db_path)
    events = store.events()
    assert [e.kind for e in events if e.kind == PENDING_DROPPED] == [PENDING_DROPPED]
    assert not any(o.status is OrderStatus.PENDING for o in store.orders())
    # Con la posición abierta y el régimen encendido no hay entradas nuevas que rechazar, pero el
    # motor recorrió las reposiciones y siguió con la vela en vivo.
    state = store.load_state(ENGINE_STATE_KEY)
    assert state is not None
    assert state["last_bar_open_time"] == candles[35].open_time
    assert state["bar_index"] == 5
    assert ReasonCode.REPLAY.value not in json.dumps(state)  # nada raro en el estado
    status = json.loads((tmp_path / "logs" / "status.json").read_text(encoding="utf-8"))
    assert status["restored_from_db"] is True
    assert "reposición" in " ".join(status["recent_events"])
    store.close()


def test_build_requires_paper_mode(tmp_path: Path) -> None:
    exchange = FakePaperExchange({BTC: rising_days(8)}, now_ms=rising_days(8)[-1].open_time)
    config = paper_config(tmp_path).model_copy(update={"mode": Mode.BACKTEST})
    with pytest.raises(ConfigError, match="mode: paper"):
        build_paper_session(config, exchange, sleep=exchange.sleep)


async def test_watchdog_and_dead_task_stop_the_session(tmp_path: Path) -> None:
    candles = rising_days(8)
    exchange = FakePaperExchange({BTC: candles}, now_ms=candles[30].open_time + 300_000)
    exchange.last[BTC] = "105"
    stale_calls: list[int] = []
    session = build_paper_session(paper_config(tmp_path), exchange, sleep=exchange.sleep)
    session.on_stale = lambda: stale_calls.append(exchange.now)
    assert not session.is_stale()
    exchange.now += 2 * 4 * 3_600_000 + 300_001  # 2 x timeframe + gracia, sin ciclos
    assert session.is_stale()
    session._handle_stale()
    assert stale_calls == [exchange.now]
    status = json.loads((tmp_path / "logs" / "status.json").read_text(encoding="utf-8"))
    assert status["phase"] == "colgado"

    # Una tarea auxiliar que muere con excepción pide la parada ordenada.
    async def boom() -> None:
        msg = "watcher roto"
        raise RuntimeError(msg)

    task = asyncio.get_running_loop().create_task(boom())
    with contextlib.suppress(RuntimeError):
        await task
    session._task_done("watcher", task)
    assert any("watcher" in line and "caída" in line for line in session.recent)
    bars = [bar async for bar in session.feed]  # el feed ya está parado
    assert bars == []
    session.store.close()
