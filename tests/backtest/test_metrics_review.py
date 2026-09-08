"""Semántica de `longest_underwater_days` y del drawdown anual con pico arrastrado."""

from __future__ import annotations

import pytest

from tests.factories import d
from tradingbot.backtest import max_drawdown
from tradingbot.backtest.metrics import DAY_MS, yearly_breakdown

D0 = 1_704_067_200_000  # 2024-01-01T00:00Z


def test_longest_underwater_is_not_necessarily_the_deepest() -> None:
    # tramo 1: caída del 30 % y recuperación en 2 días; tramo 2: caída del 5 % durante 6 días
    values = ["100", "70", "100", "99", "98", "97", "96", "95", "96", "100"]
    equity = [(D0 + i * DAY_MS, d(v)) for i, v in enumerate(values)]
    depth, longest = max_drawdown(equity)
    assert depth == pytest.approx(0.30)
    assert longest == pytest.approx(7.0)  # desde el pico del día 2 hasta recuperar en el día 9


def test_yearly_drawdown_carries_the_previous_peak() -> None:
    dec_30 = 1_703_980_800_000 - DAY_MS  # 2023-12-30T00:00Z
    equity = [
        (dec_30, d("100")),
        (dec_30 + DAY_MS, d("120")),  # pico el 31 de diciembre
        (dec_30 + 2 * DAY_MS, d("90")),  # valle el 1 de enero
        (dec_30 + 3 * DAY_MS, d("95")),
    ]
    rows = yearly_breakdown(equity, [])
    assert [r["year"] for r in rows] == [2023, 2024]
    assert rows[0]["max_drawdown"] == pytest.approx(0.0)
    # medido contra el pico de diciembre (120), no contra el primer punto de enero (90)
    assert rows[1]["max_drawdown"] == pytest.approx(1 - 90 / 120)
    assert rows[1]["return"] == pytest.approx(95 / 120 - 1)
