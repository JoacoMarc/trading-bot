"""Puerto `Notifier` (ADR-0012): niveles, `LogNotifier` y coerción de los booleanos de YAML."""

from __future__ import annotations

import asyncio
import logging

import pytest

from tradingbot.notify import (
    DEFAULT_LEVELS,
    Category,
    Level,
    LogNotifier,
    Notification,
    resolve_level,
)
from tradingbot.notify.base import TELEGRAM_TEXT_MAX, coerce_level, truncate


def test_every_category_has_a_default_level() -> None:
    assert set(DEFAULT_LEVELS) == set(Category)
    assert DEFAULT_LEVELS[Category.REJECTION] is Level.SILENT
    assert DEFAULT_LEVELS[Category.FEED] is Level.SILENT
    assert all(
        DEFAULT_LEVELS[c] is Level.ON
        for c in Category
        if c not in (Category.REJECTION, Category.FEED)
    )


def test_resolve_level_falls_back_to_defaults() -> None:
    levels = {Category.ENTRY: Level.OFF}
    assert resolve_level(levels, Category.ENTRY) is Level.OFF
    assert resolve_level(levels, Category.FEED) is Level.SILENT
    assert resolve_level({}, Category.DAILY) is Level.ON


def test_coerce_level_maps_yaml_booleans() -> None:
    # PyYAML lee `on`/`off` como True/False: vuelven a su nivel.
    assert coerce_level(True) == "on"
    assert coerce_level(False) == "off"
    assert coerce_level("silent") == "silent"


def test_truncate_respects_telegram_limit() -> None:
    assert truncate("abc") == "abc"
    long = "x" * (TELEGRAM_TEXT_MAX + 10)
    cut = truncate(long)
    assert len(cut) == TELEGRAM_TEXT_MAX
    assert cut.endswith("...")


async def test_log_notifier_logs_counts_and_skips_off(caplog: pytest.LogCaptureFixture) -> None:
    notifier = LogNotifier({Category.FEED: Level.OFF})
    task = asyncio.create_task(notifier.run())
    await asyncio.sleep(0)
    with caplog.at_level(logging.INFO, logger="tradingbot.notify.base"):
        notifier.notify(Notification(ts=1, category=Category.ENTRY, text="compra BTC"))
        notifier.notify(Notification(ts=2, category=Category.FEED, text="feed_late"))
    assert "compra BTC" in caplog.text
    assert "feed_late" not in caplog.text
    assert notifier.status() == {
        "backend": "log",
        "sent": 1,
        "errors": 0,
        "dropped": 0,
        "queued": 0,
    }
    notifier.stop()
    await asyncio.wait_for(task, 1.0)


async def test_log_notifier_stop_before_run_returns_immediately() -> None:
    notifier = LogNotifier()
    notifier.stop()
    await asyncio.wait_for(notifier.run(), 1.0)
