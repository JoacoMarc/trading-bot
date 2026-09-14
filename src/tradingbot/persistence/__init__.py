"""Persistencia: escritura atómica de archivos (Fase 2), `TradeStore` (Fase 4) y SQLite (Fase 7)."""

from tradingbot.persistence.files import atomic_write_bytes, atomic_write_text
from tradingbot.persistence.sqlite import SCHEMA_VERSION, SqliteStore
from tradingbot.persistence.store import EventRecord, InMemoryStore, TradeStore

__all__ = [
    "SCHEMA_VERSION",
    "EventRecord",
    "InMemoryStore",
    "SqliteStore",
    "TradeStore",
    "atomic_write_bytes",
    "atomic_write_text",
]
