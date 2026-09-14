"""Ventanas IS/OOS y encadenado de la curva OOS (ADR-0008), sin correr el motor."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from itertools import pairwise

import pytest

from tradingbot.config.models import ValidationConfig
from tradingbot.domain.errors import ConfigError
from tradingbot.validation.walkforward import (
    WalkForwardSettings,
    add_months,
    build_windows,
    chain_equity,
)


def test_add_months_clamps_day_to_month_end() -> None:
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert add_months(date(2019, 8, 1), 24) == date(2021, 8, 1)
    assert add_months(date(2023, 11, 30), 3) == date(2024, 2, 29)
    assert add_months(date(2023, 12, 15), 13) == date(2025, 1, 15)


def test_rolling_windows_are_complete_and_contiguous() -> None:
    windows = build_windows(date(2019, 8, 1), date(2025, 9, 1), is_months=24, oos_months=6)
    assert len(windows) == 8
    first, last = windows[0], windows[-1]
    assert (first.is_start, first.is_end) == (date(2019, 8, 1), date(2021, 8, 1))
    assert (first.oos_start, first.oos_end) == (date(2021, 8, 1), date(2022, 2, 1))
    assert last.oos_end == date(2025, 8, 1)  # la ventana siguiente pisaría el fin del rango
    for previous, current in pairwise(windows):
        assert current.oos_start == previous.oos_end  # tramos OOS contiguos
        assert current.is_start == add_months(previous.is_start, 6)
        assert current.is_end == current.oos_start
    assert [w.index for w in windows] == list(range(8))


def test_anchored_windows_grow_the_in_sample() -> None:
    windows = build_windows(
        date(2019, 8, 1), date(2025, 9, 1), is_months=24, oos_months=6, anchored=True
    )
    assert len(windows) == 8
    assert all(w.is_start == date(2019, 8, 1) for w in windows)
    assert [w.is_end for w in windows][:3] == [
        date(2021, 8, 1),
        date(2022, 2, 1),
        date(2022, 8, 1),
    ]


def test_windows_require_enough_range() -> None:
    with pytest.raises(ConfigError, match="no alcanza"):
        build_windows(date(2024, 1, 1), date(2024, 12, 1), is_months=24, oos_months=6)
    with pytest.raises(ConfigError, match="positivos"):
        build_windows(date(2019, 1, 1), date(2025, 1, 1), is_months=0, oos_months=6)


def test_chain_equity_rescales_each_segment_to_the_previous_end() -> None:
    first = [(1, Decimal(100)), (2, Decimal(110))]
    second = [(2, Decimal(50)), (3, Decimal(55)), (4, Decimal(44))]  # arranca en 50: x2.2
    chained = chain_equity([first, second, []], Decimal(100))
    assert chained == [
        (1, Decimal(100)),
        (2, Decimal(110)),
        (3, Decimal("121.0")),
        (4, Decimal("96.8")),
    ]


def test_chain_equity_rejects_non_positive_base() -> None:
    with pytest.raises(ValueError, match="cero o negativo"):
        chain_equity([[(1, Decimal(0)), (2, Decimal(5))]], Decimal(100))


def test_chain_equity_compounds_segment_returns() -> None:
    segments = [
        [(1, Decimal(1000)), (2, Decimal(1100))],  # +10 %
        [(3, Decimal(500)), (4, Decimal(450))],  # -10 %
        [(5, Decimal(200)), (6, Decimal(260))],  # +30 %
    ]
    chained = chain_equity(segments, Decimal(1000))
    assert len(chained) == sum(len(s) for s in segments)
    assert chained[-1][1] == Decimal(1000) * Decimal("1.1") * Decimal("0.9") * Decimal("1.3")


def test_settings_take_trade_thresholds_from_config() -> None:
    cfg = ValidationConfig(trades_full_min=30, trades_oos_min=15)
    settings = WalkForwardSettings.from_config(cfg)
    assert settings.thresholds.trades_full_min == 30
    assert settings.thresholds.trades_oos_min == 15
    assert settings.to_config_dict()["trades_oos_min"] == 15
    assert WalkForwardSettings.from_config(ValidationConfig()).thresholds.trades_full_min == 100
