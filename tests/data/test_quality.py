"""QualityChecker: huecos, duplicados, alineación, OHLC y registro de huecos conocidos."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tests.factories import BTC, ETH, H4_MS, T0, make_series
from tradingbot.data import Gap, GapRegistry, candles_to_frame, check_frame, find_gaps
from tradingbot.domain import DataError, Timeframe


def test_clean_series_has_no_findings() -> None:
    report = check_frame(candles_to_frame(make_series(n=10)), BTC, Timeframe.H4)
    assert report.rows == 10
    assert report.structural_ok
    assert report.gaps == ()
    assert report.is_clean()
    assert report.findings() == []


def test_find_gaps_reports_missing_open_times() -> None:
    times = np.array([T0 + i * H4_MS for i in (0, 1, 4, 5, 9)], dtype="int64")
    gaps = find_gaps(times, Timeframe.H4)
    assert gaps == (Gap(T0 + 2 * H4_MS, T0 + 3 * H4_MS), Gap(T0 + 6 * H4_MS, T0 + 8 * H4_MS))
    assert gaps[0].missing(Timeframe.H4) == 2
    assert gaps[1].missing(Timeframe.H4) == 3
    assert "3 velas" in gaps[1].describe(Timeframe.H4)


def test_gap_registry_hides_known_gaps() -> None:
    frame = candles_to_frame(make_series(n=10, skip=frozenset({3, 4, 7})))
    report = check_frame(frame, BTC, Timeframe.H4)
    assert len(report.gaps) == 2
    assert not report.is_clean()
    known = [Gap(T0 + 3 * H4_MS, T0 + 4 * H4_MS)]
    assert report.unregistered_gaps(known) == (Gap(T0 + 7 * H4_MS, T0 + 7 * H4_MS),)
    wider = [Gap(T0 + 2 * H4_MS, T0 + 8 * H4_MS)]  # un registro que cubre ambos huecos
    assert report.is_clean(wider)
    findings = report.findings(known)
    assert len(findings) == 1
    assert findings[0].startswith("hueco no registrado")


def test_structural_problems_are_detected() -> None:
    frame = candles_to_frame(make_series(n=4))
    frame.loc[3, "open_time"] = T0 + 1  # desalineado y desordenado
    frame.loc[2, "open_time"] = T0  # duplicado
    lows = list(frame["low"])
    lows[1] = Decimal("500")  # OHLC roto
    frame["low"] = pd.Series(lows, dtype="object")
    volumes = list(frame["volume"])
    volumes[0] = Decimal("0")
    frame["volume"] = pd.Series(volumes, dtype="object")
    report = check_frame(frame, BTC, Timeframe.H4)
    assert report.duplicates == 1
    assert report.misaligned == 1
    assert report.unsorted
    assert report.invalid_ohlc == 1
    assert report.zero_volume == 1
    assert not report.structural_ok
    assert len(report.findings()) == 4


def test_empty_frame_report() -> None:
    report = check_frame(candles_to_frame([]), BTC, Timeframe.H4)
    assert report.rows == 0
    assert report.findings() == ["sin datos"]


def test_gap_registry_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "gaps.json"
    assert GapRegistry.load(path).entries == {}
    registry = GapRegistry()
    assert registry.add(BTC, Timeframe.H4, Gap(T0, T0 + H4_MS), "mantenimiento")
    assert not registry.add(BTC, Timeframe.H4, Gap(T0, T0), "cubierto")
    assert registry.add(ETH, Timeframe.H1, Gap(T0, T0), "otro")
    registry.save(path)
    text = path.read_text(encoding="utf-8")
    assert '"pair": "BTC/USDT"' in text
    assert '"missing": 2' in text
    loaded = GapRegistry.load(path)
    assert loaded.known(BTC, Timeframe.H4) == [Gap(T0, T0 + H4_MS)]
    assert loaded.known(ETH, Timeframe.H1) == [Gap(T0, T0)]
    assert loaded.known(ETH, Timeframe.H4) == []


def test_gap_registry_rejects_invalid_entries(tmp_path: Path) -> None:
    path = tmp_path / "gaps.json"
    path.write_text(
        '{"gaps": [{"pair": "BTC/USDT", "timeframe": "4h", "start_ms": 1, "end_ms": 0}]}'
    )
    with pytest.raises(DataError, match="inválido"):
        GapRegistry.load(path)
    path.write_text("{not json")
    with pytest.raises(DataError, match="ilegible"):
        GapRegistry.load(path)


def test_repo_gap_registry_is_valid() -> None:
    root = Path(__file__).resolve().parents[2]
    registry = GapRegistry.load(root / "configs" / "binance_gaps.json")
    assert registry.exchange == "binance"
