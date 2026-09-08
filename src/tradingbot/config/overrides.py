"""Overrides de línea de comandos.

Ejemplo: `--set risk.max_positions=2 --set strategy.params.ema_fast=15`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import yaml

from tradingbot.domain.errors import ConfigError


def parse_set(items: Iterable[str]) -> dict[str, Any]:
    """Convierte `clave.anidada=valor` en un dict anidado.

    El valor se interpreta como escalar YAML: `2` → int, `0.5` → float, `true` → bool,
    `BTC/USDT` → str, `[a, b]` → lista. Para forzar texto, usar comillas: `name="007"`.
    """
    result: dict[str, Any] = {}
    for item in items:
        key, sep, raw = item.partition("=")
        key = key.strip()
        if not sep or not key:
            msg = f"override inválido {item!r}; formato esperado clave.subclave=valor"
            raise ConfigError(msg)
        try:
            value = yaml.safe_load(raw.strip()) if raw.strip() else ""
        except yaml.YAMLError as exc:
            msg = f"valor inválido en override {item!r}: {exc}"
            raise ConfigError(msg) from exc
        _assign(result, key.split("."), value)
    return result


def _assign(target: dict[str, Any], path: list[str], value: Any) -> None:
    head, *rest = path
    if not head:
        msg = "override con clave vacía"
        raise ConfigError(msg)
    if not rest:
        target[head] = value
        return
    child = target.setdefault(head, {})
    if not isinstance(child, dict):
        msg = f"conflicto en override: {head!r} ya tiene un valor escalar"
        raise ConfigError(msg)
    _assign(child, rest, value)


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Mezcla recursiva; los valores de `override` ganan."""
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            merged[key] = deep_merge(current, value)
        else:
            merged[key] = value
    return merged
