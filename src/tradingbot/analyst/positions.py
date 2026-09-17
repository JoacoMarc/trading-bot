"""Snapshots observacionales de una cuenta paper, sin permisos de escritura."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tradingbot.decision.models import PositionContext
from tradingbot.domain.positions import Position


def read_positions(path: Path, now: int) -> dict[str, PositionContext]:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        state = dict(
            connection.execute("SELECT key,value FROM state WHERE key IN ('session','engine')")
        )
        session, engine = json.loads(state["session"]), json.loads(state["engine"])
        saved_at = int(session["saved_ts"])
        if session["mode"] != "paper" or not 0 <= now - saved_at <= 14_700_000:
            raise ValueError("sesión de origen no paper, futura o desactualizada")
        positions = [
            Position.model_validate_json(row[0])
            for row in connection.execute("SELECT data FROM positions")
        ]
        return {
            p.pair.symbol: PositionContext(
                qty=p.qty,
                entry_price=p.entry_price,
                entry_time=p.entry_time,
                stop_price=p.stop_price,
                cash=engine["cash"],
                source_saved_at=saved_at,
            )
            for p in positions
            if p.strategy == "donchian"
        }
    finally:
        connection.close()
