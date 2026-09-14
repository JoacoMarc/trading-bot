"""`status.json`: escritura atómica, lectura y heartbeat vencido."""

from __future__ import annotations

from pathlib import Path

from tradingbot.observability import (
    STATUS_VERSION,
    StatusWriter,
    heartbeat_age_ms,
    is_stale,
    read_status,
)

H4_MS = 4 * 3_600_000


def test_write_read_and_staleness(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "status.json"
    writer = StatusWriter(path)
    assert read_status(path) is None
    written = writer.write({"mode": "paper", "timeframe_ms": H4_MS}, heartbeat_ts=1_700_000_000_000)
    assert written["version"] == STATUS_VERSION
    loaded = read_status(path)
    assert loaded is not None
    assert loaded["heartbeat_ts"] == 1_700_000_000_000
    assert loaded["heartbeat_utc"].endswith("UTC")
    assert heartbeat_age_ms(loaded, 1_700_000_060_000) == 60_000
    assert not is_stale(loaded, 1_700_000_000_000 + 2 * H4_MS)  # dentro de 2 x timeframe
    assert is_stale(loaded, 1_700_000_000_000 + 2 * H4_MS + 300_001)  # pasada la gracia
    assert is_stale({"mode": "paper"}, 0)  # sin heartbeat ni timeframe: vencido
    assert is_stale({"heartbeat_ts": 0}, 0)
    # Reescribir reemplaza el archivo entero (sin restos del anterior).
    writer.write({"mode": "paper", "timeframe_ms": H4_MS, "phase": "detenido"}, heartbeat_ts=5)
    again = read_status(path)
    assert again is not None
    assert again["phase"] == "detenido"
    assert again["heartbeat_ts"] == 5
