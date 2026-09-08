import time

import pytest

from tradingbot.engine import Clock, RealClock, SimClock


def test_real_clock_is_epoch_ms() -> None:
    clock: Clock = RealClock()
    now = clock.now_ms()
    assert abs(now - int(time.time() * 1000)) < 5_000


def test_real_clock_applies_exchange_offset() -> None:
    clock = RealClock(offset_ms=-400)
    assert clock.offset_ms == -400
    clock.set_offset(60_000)
    assert clock.now_ms() - int(time.time() * 1000) > 55_000


def test_sim_clock_advances_monotonically() -> None:
    clock = SimClock(start_ms=1_000)
    assert clock.now_ms() == 1_000
    clock.advance(500)
    assert clock.now_ms() == 1_500
    clock.advance_to(1_500)
    clock.advance_to(2_000)
    assert clock.now_ms() == 2_000
    with pytest.raises(ValueError, match="no retrocede"):
        clock.advance_to(1_999)
    with pytest.raises(ValueError, match="negativo"):
        clock.advance(-1)
    with pytest.raises(ValueError, match="negativo"):
        SimClock(start_ms=-1)
