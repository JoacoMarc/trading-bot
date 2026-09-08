"""tradingbot: bot de trading propio para Binance Spot."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tradingbot")
except PackageNotFoundError:  # pragma: no cover - solo si el paquete no está instalado
    __version__ = "0.0.0+local"

__all__ = ["__version__"]
