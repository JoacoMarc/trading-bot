"""Persistencia. Fase 2: escritura atómica de archivos; `TradeStore` llega en la Fase 4."""

from tradingbot.persistence.files import atomic_write_bytes, atomic_write_text

__all__ = ["atomic_write_bytes", "atomic_write_text"]
