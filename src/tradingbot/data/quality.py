"""Chequeo de calidad de los datos almacenados.

Detecta huecos (velas faltantes entre la primera y la última), duplicados, `open_time` no
alineados, desorden y OHLC inconsistentes. Los huecos reales de Binance (mantenimientos,
caídas) se registran en un archivo versionado (`configs/binance_gaps.json`) para que
`data-check` solo alerte por lo que no está explicado.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tradingbot.data.store import iter_rows
from tradingbot.domain.errors import DataError
from tradingbot.domain.pair import Pair
from tradingbot.domain.timeframe import Timeframe
from tradingbot.persistence.files import atomic_write_text

GAPS_VERSION = 1


def _iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True, order=True)
class Gap:
    """Velas faltantes desde `start_ms` hasta `end_ms`, ambos `open_time` inclusive."""

    start_ms: int
    end_ms: int

    def missing(self, timeframe: Timeframe) -> int:
        return (self.end_ms - self.start_ms) // timeframe.ms + 1

    def covers(self, other: Gap) -> bool:
        return self.start_ms <= other.start_ms and other.end_ms <= self.end_ms

    def describe(self, timeframe: Timeframe) -> str:
        return f"{_iso(self.start_ms)} -> {_iso(self.end_ms)} ({self.missing(timeframe)} velas)"


@dataclass(frozen=True, slots=True)
class QualityReport:
    pair: Pair
    timeframe: Timeframe
    rows: int
    first_open_time: int | None
    last_open_time: int | None
    gaps: tuple[Gap, ...] = ()
    duplicates: int = 0
    misaligned: int = 0
    unsorted: bool = False
    invalid_ohlc: int = 0
    zero_volume: int = 0

    @property
    def structural_ok(self) -> bool:
        """Sin duplicados, desalineados, desorden ni OHLC inválidos (los huecos van aparte)."""
        return not (self.duplicates or self.misaligned or self.unsorted or self.invalid_ohlc)

    def unregistered_gaps(self, known: Iterable[Gap]) -> tuple[Gap, ...]:
        known_list = list(known)
        return tuple(g for g in self.gaps if not any(k.covers(g) for k in known_list))

    def is_clean(self, known: Iterable[Gap] = ()) -> bool:
        return self.structural_ok and not self.unregistered_gaps(known)

    def findings(self, known: Iterable[Gap] = ()) -> list[str]:
        """Hallazgos legibles; lista vacía = limpio."""
        out: list[str] = []
        if self.rows == 0:
            out.append("sin datos")
            return out
        if self.unsorted:
            out.append("open_time desordenado")
        if self.duplicates:
            out.append(f"{self.duplicates} open_time duplicados")
        if self.misaligned:
            out.append(f"{self.misaligned} open_time no alineados a {self.timeframe.value}")
        if self.invalid_ohlc:
            out.append(f"{self.invalid_ohlc} velas con OHLC inconsistente")
        for gap in self.unregistered_gaps(known):
            out.append(f"hueco no registrado {gap.describe(self.timeframe)}")
        return out


def find_gaps(open_times: np.ndarray, timeframe: Timeframe) -> tuple[Gap, ...]:
    """Huecos entre `open_time`s consecutivos (ordenados y únicos)."""
    if len(open_times) < 2:
        return ()
    step = timeframe.ms
    diffs = np.diff(open_times)
    idx = np.nonzero(diffs > step)[0]
    return tuple(
        Gap(int(open_times[i]) + step, int(open_times[i + 1]) - step) for i in idx.tolist()
    )


def check_frame(frame: pd.DataFrame, pair: Pair, timeframe: Timeframe) -> QualityReport:
    """Analiza un frame del store (columnas `open_time`, OHLCV en Decimal)."""
    rows = len(frame)
    if rows == 0:
        return QualityReport(pair, timeframe, 0, None, None)
    times = frame["open_time"].to_numpy(dtype="int64")
    unsorted = bool((times[1:] < times[:-1]).any())
    unique_times, counts = np.unique(times, return_counts=True)
    duplicates = int((counts - 1).sum())
    misaligned = int(((unique_times % timeframe.ms) != 0).sum())
    invalid = 0
    zero_volume = 0
    for _, open_, high, low, close, volume in iter_rows(frame):
        if low > high or not (low <= open_ <= high) or not (low <= close <= high) or low <= 0:
            invalid += 1
        if volume == 0:
            zero_volume += 1
    return QualityReport(
        pair=pair,
        timeframe=timeframe,
        rows=rows,
        first_open_time=int(unique_times[0]),
        last_open_time=int(unique_times[-1]),
        gaps=find_gaps(unique_times, timeframe),
        duplicates=duplicates,
        misaligned=misaligned,
        unsorted=unsorted,
        invalid_ohlc=invalid,
        zero_volume=zero_volume,
    )


@dataclass
class GapRegistry:
    """Huecos conocidos por `(par, timeframe)`, persistidos en JSON versionado."""

    exchange: str = "binance"
    entries: dict[tuple[Pair, Timeframe], list[tuple[Gap, str]]] = field(default_factory=dict)

    def known(self, pair: Pair, timeframe: Timeframe) -> list[Gap]:
        return [gap for gap, _ in self.entries.get((pair, timeframe), [])]

    def add(self, pair: Pair, timeframe: Timeframe, gap: Gap, note: str) -> bool:
        """Agrega el hueco si no está cubierto por uno ya registrado. Devuelve si agregó."""
        current = self.entries.setdefault((pair, timeframe), [])
        if any(k.covers(gap) for k, _ in current):
            return False
        current.append((gap, note))
        current.sort(key=lambda item: item[0])
        return True

    @classmethod
    def load(cls, path: Path) -> GapRegistry:
        """Lee el registro; un archivo inexistente equivale a un registro vacío."""
        if not path.is_file():
            return cls()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            msg = f"registro de huecos ilegible {path}: {exc}"
            raise DataError(msg) from exc
        registry = cls(exchange=str(payload.get("exchange", "binance")))
        for raw in payload.get("gaps", []):
            try:
                pair = Pair.parse(str(raw["pair"]))
                timeframe = Timeframe.parse(str(raw["timeframe"]))
                gap = Gap(int(raw["start_ms"]), int(raw["end_ms"]))
            except (KeyError, ValueError, TypeError) as exc:
                msg = f"entrada inválida en {path}: {raw!r}"
                raise DataError(msg) from exc
            aligned = timeframe.is_aligned(gap.start_ms) and timeframe.is_aligned(gap.end_ms)
            if gap.end_ms < gap.start_ms or not aligned:
                msg = f"hueco inválido en {path}: {raw!r}"
                raise DataError(msg)
            registry.add(pair, timeframe, gap, str(raw.get("note", "")))
        return registry

    def to_payload(self) -> dict[str, Any]:
        gaps: list[dict[str, Any]] = []
        for (pair, timeframe), items in sorted(
            self.entries.items(), key=lambda kv: (kv[0][0].symbol, kv[0][1].ms)
        ):
            for gap, note in items:
                gaps.append(
                    {
                        "pair": pair.symbol,
                        "timeframe": timeframe.value,
                        "start_ms": gap.start_ms,
                        "end_ms": gap.end_ms,
                        "start": _iso(gap.start_ms),
                        "end": _iso(gap.end_ms),
                        "missing": gap.missing(timeframe),
                        "note": note,
                    }
                )
        return {"version": GAPS_VERSION, "exchange": self.exchange, "gaps": gaps}

    def save(self, path: Path) -> None:
        text = json.dumps(self.to_payload(), indent=2, ensure_ascii=False) + "\n"
        atomic_write_text(path, text)
