"""Par de trading. En v1 el quote es siempre USDT (ADR-0004)."""

from __future__ import annotations

import re
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

ALLOWED_QUOTES: frozenset[str] = frozenset({"USDT"})
# Binance lista activos de una sola letra (p. ej. `T`) y de hasta ~10 (`1MBABYDOGE`).
_ASSET_RE = re.compile(r"^[A-Z0-9]{1,12}$")


class Pair(BaseModel):
    """Par `base/quote`, p. ej. BTC/USDT. Inmutable y hashable (se usa como clave de `Bar`)."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    base: str
    quote: str

    @field_validator("base", "quote")
    @classmethod
    def _upper_and_valid(cls, value: str) -> str:
        upper = value.upper()
        if not _ASSET_RE.match(upper):
            msg = f"activo inválido {value!r}"
            raise ValueError(msg)
        return upper

    @model_validator(mode="after")
    def _quote_allowed(self) -> Self:
        if self.quote not in ALLOWED_QUOTES:
            msg = f"quote {self.quote!r} no soportado en v1; permitidos: {sorted(ALLOWED_QUOTES)}"
            raise ValueError(msg)
        if self.base == self.quote:
            msg = "base y quote no pueden ser iguales"
            raise ValueError(msg)
        return self

    @property
    def symbol(self) -> str:
        """Formato ccxt: `BTC/USDT`."""
        return f"{self.base}/{self.quote}"

    @property
    def binance_symbol(self) -> str:
        """Formato nativo de Binance: `BTCUSDT`."""
        return f"{self.base}{self.quote}"

    @classmethod
    def parse(cls, text: str) -> Pair:
        """Acepta `BTC/USDT`, `BTC-USDT`, `BTC_USDT` o `BTCUSDT` (con quote permitido)."""
        cleaned = text.strip().upper()
        for sep in ("/", "-", "_"):
            if sep in cleaned:
                base, quote = cleaned.split(sep, 1)
                return cls(base=base, quote=quote)
        for quote in sorted(ALLOWED_QUOTES, key=len, reverse=True):
            if cleaned.endswith(quote) and len(cleaned) > len(quote):
                return cls(base=cleaned[: -len(quote)], quote=quote)
        msg = f"no se puede interpretar el par {text!r}"
        raise ValueError(msg)

    def __str__(self) -> str:
        return self.symbol

    def __lt__(self, other: Pair) -> bool:
        return self.symbol < other.symbol
