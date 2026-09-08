"""Jerarquía de excepciones del dominio.

Los adapters (exchange, datos, persistencia) traducen sus errores a estas clases para que el
`Engine` y el `RiskManager` razonen sobre categorías estables y no sobre detalles de ccxt.
"""

from __future__ import annotations


class TradingBotError(Exception):
    """Base de todas las excepciones del proyecto."""


class DomainError(TradingBotError):
    """Violación de una invariante del dominio (vela inválida, cantidad negativa, etc.)."""


class ConfigError(TradingBotError):
    """Configuración inválida o incompleta para el modo elegido."""


class DataError(TradingBotError):
    """Problemas con los datos de mercado almacenados o descargados."""


class InsufficientWarmup(DataError):
    """No hay velas suficientes antes de `from` para el warmup de la estrategia."""


class ExchangeError(TradingBotError):
    """Base de los errores provenientes del exchange."""


class ExchangeUnavailable(ExchangeError):
    """Red caída, mantenimiento o timeout. Reintentable con backoff."""


class RateLimited(ExchangeError):
    """El exchange pidió bajar el ritmo (429/418). Reintentable tras esperar."""


class InsufficientFunds(ExchangeError):
    """Saldo insuficiente para la orden. No reintentar a ciegas."""


class InvalidOrder(ExchangeError):
    """Orden rechazada por filtros (precisión, notional, precio) o inexistente. No reintentar."""


class AuthError(ExchangeError):
    """Clave inválida, sin permisos o de otro entorno (testnet vs producción). No reintentar."""
