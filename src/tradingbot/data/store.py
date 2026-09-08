"""Almacenamiento de velas en parquet: un archivo por `exchange/PAR/timeframe`.

Esquema fijo (ADR-0005): `open_time` int64 (ms UTC) + OHLCV en `decimal128(24, 8)`. Binance
publica precios y cantidades con hasta 8 decimales, así que el parquet conserva exactamente lo
que devolvió el exchange y la lectura entrega `Decimal` sin pasar por float (ADR-0003). La
conversión a `float64` para indicadores ocurre en `indicators/` (Fase 3), no acá.

Escrituras atómicas (archivo temporal + `os.replace`) y `upsert` por `open_time` para que la
descarga incremental sea idempotente.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from tradingbot.domain.candle import Candle
from tradingbot.domain.errors import DataError
from tradingbot.domain.pair import Pair
from tradingbot.domain.timeframe import Timeframe

SCHEMA_VERSION = 1
DECIMAL_SCALE = 8
DECIMAL_TYPE = pa.decimal128(24, DECIMAL_SCALE)
PRICE_COLUMNS: tuple[str, ...] = ("open", "high", "low", "close", "volume")
COLUMNS: tuple[str, ...] = ("open_time", *PRICE_COLUMNS)
OHLCV_SCHEMA = pa.schema(
    [pa.field("open_time", pa.int64(), nullable=False)]
    + [pa.field(name, DECIMAL_TYPE, nullable=False) for name in PRICE_COLUMNS]
)
_MIN_EXPONENT = -DECIMAL_SCALE


@dataclass(frozen=True, slots=True)
class DatasetInfo:
    """Resumen de un dataset almacenado."""

    pair: Pair
    timeframe: Timeframe
    rows: int
    first_open_time: int
    last_open_time: int
    path: Path
    size_bytes: int

    @property
    def expected_rows(self) -> int:
        """Velas que habría sin huecos entre la primera y la última."""
        return (self.last_open_time - self.first_open_time) // self.timeframe.ms + 1

    @property
    def missing_rows(self) -> int:
        return self.expected_rows - self.rows


@dataclass(frozen=True, slots=True)
class UpsertResult:
    added: int
    updated: int
    unchanged: int
    total_rows: int


def empty_frame() -> pd.DataFrame:
    """DataFrame vacío con las columnas del esquema."""
    return pd.DataFrame({name: pd.Series(dtype="object") for name in COLUMNS}).astype(
        {"open_time": "int64"}
    )


def candles_to_frame(candles: Iterable[Candle]) -> pd.DataFrame:
    """Lista de `Candle` → DataFrame con el esquema del store (Decimal en OHLCV)."""
    rows = [
        (c.open_time, c.open, c.high, c.low, c.close, c.volume)
        for c in sorted(candles, key=lambda c: c.open_time)
    ]
    if not rows:
        return empty_frame()
    frame = pd.DataFrame.from_records(rows, columns=list(COLUMNS))
    frame["open_time"] = frame["open_time"].astype("int64")
    return frame


OhlcvRow = tuple[int, Decimal, Decimal, Decimal, Decimal, Decimal]


def iter_rows(frame: pd.DataFrame) -> Iterator[OhlcvRow]:
    """Filas `(open_time, open, high, low, close, volume)` con tipos concretos.

    Evita `itertuples`, cuyos atributos quedan tipados como unión gigante en pandas-stubs.
    """
    times = [int(t) for t in frame["open_time"].tolist()]
    columns: list[list[Decimal]] = [list(frame[name]) for name in PRICE_COLUMNS]
    opens, highs, lows, closes, volumes = columns
    for i, open_time in enumerate(times):
        yield (open_time, opens[i], highs[i], lows[i], closes[i], volumes[i])


def frame_to_candles(frame: pd.DataFrame, pair: Pair, timeframe: Timeframe) -> list[Candle]:
    """DataFrame del store → `Candle`s validadas."""
    return [
        Candle(
            pair=pair,
            timeframe=timeframe,
            open_time=open_time,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )
        for open_time, open_, high, low, close, volume in iter_rows(frame)
    ]


def validate_frame(frame: pd.DataFrame, timeframe: Timeframe) -> None:
    """Invariantes de un frame listo para escribir: esquema, orden, unicidad, alineación, OHLC."""
    missing = [c for c in COLUMNS if c not in frame.columns]
    if missing:
        msg = f"faltan columnas {missing}"
        raise DataError(msg)
    if frame.empty:
        return
    times = frame["open_time"].to_numpy()
    if (times[1:] <= times[:-1]).any():
        msg = "open_time debe ser estrictamente creciente (orden y sin duplicados)"
        raise DataError(msg)
    if (times < 0).any() or (times % timeframe.ms != 0).any():
        msg = f"open_time no alineado a {timeframe.value}"
        raise DataError(msg)
    for name in PRICE_COLUMNS:
        for value in frame[name]:
            if not isinstance(value, Decimal):
                msg = f"columna {name}: se esperaba Decimal, llegó {type(value).__name__}"
                raise DataError(msg)
            if not value.is_finite():
                msg = f"columna {name}: valor no finito {value}"
                raise DataError(msg)
            exponent = value.as_tuple().exponent
            if isinstance(exponent, int) and exponent < _MIN_EXPONENT:
                msg = f"columna {name}: {value} tiene más de {DECIMAL_SCALE} decimales"
                raise DataError(msg)
    for open_time, open_, high, low, close, volume in iter_rows(frame):
        if low > high or not (low <= open_ <= high) or not (low <= close <= high):
            msg = f"OHLC inconsistente en open_time={open_time}"
            raise DataError(msg)
        if low <= 0 or volume < 0:
            msg = f"precio no positivo o volumen negativo en open_time={open_time}"
            raise DataError(msg)


def _to_table(frame: pd.DataFrame, pair: Pair, timeframe: Timeframe, exchange: str) -> pa.Table:
    arrays = [pa.array(frame["open_time"].to_numpy(dtype="int64"), type=pa.int64())]
    arrays += [pa.array(list(frame[name]), type=DECIMAL_TYPE) for name in PRICE_COLUMNS]
    metadata = {
        b"tradingbot.schema_version": str(SCHEMA_VERSION).encode(),
        b"tradingbot.exchange": exchange.encode(),
        b"tradingbot.pair": pair.symbol.encode(),
        b"tradingbot.timeframe": timeframe.value.encode(),
    }
    return pa.Table.from_arrays(arrays, schema=OHLCV_SCHEMA.with_metadata(metadata))


def _from_table(table: pa.Table) -> pd.DataFrame:
    missing = [c for c in COLUMNS if c not in table.column_names]
    if missing:
        msg = f"parquet con esquema ajeno: faltan columnas {missing}"
        raise DataError(msg)
    frame: pd.DataFrame = table.select(list(COLUMNS)).to_pandas()
    frame["open_time"] = frame["open_time"].astype("int64")
    return frame.reset_index(drop=True)


def write_parquet(
    path: Path, frame: pd.DataFrame, pair: Pair, timeframe: Timeframe, exchange: str = "binance"
) -> int:
    """Escribe un frame validado en `path` de forma atómica. Devuelve filas escritas."""
    frame = frame.loc[:, list(COLUMNS)].sort_values("open_time").reset_index(drop=True)
    validate_frame(frame, timeframe)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Mismo patrón que `persistence.files.atomic_write_*`, pero pyarrow escribe directo al tmp.
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        pq.write_table(_to_table(frame, pair, timeframe, exchange), tmp, compression="zstd")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return len(frame)


def read_parquet(
    path: Path, start_ms: int | None = None, end_ms: int | None = None
) -> pd.DataFrame:
    """Lee un parquet del esquema del store con `start_ms ≤ open_time < end_ms`."""
    filters: list[tuple[str, str, int]] = []
    if start_ms is not None:
        filters.append(("open_time", ">=", start_ms))
    if end_ms is not None:
        filters.append(("open_time", "<", end_ms))
    try:
        table = pq.read_table(path, filters=filters or None)
    except (pa.ArrowInvalid, OSError) as exc:
        msg = f"no se pudo leer {path}: {exc}"
        raise DataError(msg) from exc
    return _from_table(table)


def read_parquet_metadata(path: Path) -> dict[str, str]:
    """Metadatos `tradingbot.*` guardados en el esquema (exchange, par, timeframe, versión)."""
    schema = pq.read_schema(path)
    raw = schema.metadata or {}
    return {
        k.decode()[len("tradingbot.") :]: v.decode()
        for k, v in raw.items()
        if k.startswith(b"tradingbot.")
    }


class ParquetStore:
    """Velas históricas en `root/<exchange>/<BASEQUOTE>/<timeframe>.parquet`."""

    def __init__(self, root: Path | str, exchange: str = "binance") -> None:
        self.root = Path(root)
        self.exchange = exchange

    # ------------------------------------------------------------- rutas

    @property
    def exchange_dir(self) -> Path:
        return self.root / self.exchange

    def path(self, pair: Pair, timeframe: Timeframe) -> Path:
        return self.exchange_dir / pair.binance_symbol / f"{timeframe.value}.parquet"

    def exists(self, pair: Pair, timeframe: Timeframe) -> bool:
        return self.path(pair, timeframe).is_file()

    def list_datasets(self) -> list[tuple[Pair, Timeframe]]:
        """Datasets presentes, ordenados por par y timeframe."""
        found: list[tuple[Pair, Timeframe]] = []
        if not self.exchange_dir.is_dir():
            return found
        for pair_dir in sorted(self.exchange_dir.iterdir()):
            if not pair_dir.is_dir():
                continue
            try:
                pair = Pair.parse(pair_dir.name)
            except ValueError:
                continue
            for file in sorted(pair_dir.glob("*.parquet")):
                try:
                    timeframe = Timeframe.parse(file.stem)
                except ValueError:
                    continue
                found.append((pair, timeframe))
        found.sort(key=lambda item: (item[0].symbol, item[1].ms))
        return found

    # ------------------------------------------------------------- lectura

    def read(
        self,
        pair: Pair,
        timeframe: Timeframe,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> pd.DataFrame:
        """Velas con `start_ms ≤ open_time < end_ms`. Sin archivo → frame vacío."""
        path = self.path(pair, timeframe)
        if not path.is_file():
            return empty_frame()
        return read_parquet(path, start_ms, end_ms)

    def read_candles(
        self,
        pair: Pair,
        timeframe: Timeframe,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> list[Candle]:
        return frame_to_candles(self.read(pair, timeframe, start_ms, end_ms), pair, timeframe)

    def info(self, pair: Pair, timeframe: Timeframe) -> DatasetInfo | None:
        """Filas y rango del dataset leyendo solo la columna `open_time`."""
        path = self.path(pair, timeframe)
        if not path.is_file():
            return None
        try:
            table = pq.read_table(path, columns=["open_time"])
        except (pa.ArrowInvalid, OSError) as exc:
            msg = f"no se pudo leer {path}: {exc}"
            raise DataError(msg) from exc
        rows = table.num_rows
        if rows == 0:
            return None
        times = table.column("open_time").to_pylist()
        return DatasetInfo(
            pair=pair,
            timeframe=timeframe,
            rows=rows,
            first_open_time=int(min(times)),
            last_open_time=int(max(times)),
            path=path,
            size_bytes=path.stat().st_size,
        )

    # ------------------------------------------------------------- escritura

    def write(self, pair: Pair, timeframe: Timeframe, frame: pd.DataFrame) -> int:
        """Reemplaza el dataset completo. Devuelve filas escritas."""
        return write_parquet(self.path(pair, timeframe), frame, pair, timeframe, self.exchange)

    def write_candles(self, pair: Pair, timeframe: Timeframe, candles: Sequence[Candle]) -> int:
        return self.write(pair, timeframe, candles_to_frame(candles))

    def upsert(self, pair: Pair, timeframe: Timeframe, frame: pd.DataFrame) -> UpsertResult:
        """Inserta o reemplaza por `open_time`. Lo nuevo gana sobre lo existente."""
        incoming = frame.loc[:, list(COLUMNS)].copy()
        if incoming.empty:
            existing_info = self.info(pair, timeframe)
            return UpsertResult(0, 0, 0, existing_info.rows if existing_info else 0)
        incoming = incoming.drop_duplicates("open_time", keep="last").sort_values("open_time")
        existing = self.read(pair, timeframe)
        if existing.empty:
            total = self.write(pair, timeframe, incoming)
            return UpsertResult(added=total, updated=0, unchanged=0, total_rows=total)

        old_by_time = {row[0]: row[1:] for row in iter_rows(existing)}
        added = updated = unchanged = 0
        for row in iter_rows(incoming):
            old = old_by_time.get(row[0])
            if old is None:
                added += 1
            elif old != row[1:]:
                updated += 1
            else:
                unchanged += 1
        merged = (
            pd.concat([existing, incoming], ignore_index=True)
            .drop_duplicates("open_time", keep="last")
            .sort_values("open_time")
            .reset_index(drop=True)
        )
        total = self.write(pair, timeframe, merged)
        return UpsertResult(added=added, updated=updated, unchanged=unchanged, total_rows=total)

    def upsert_candles(
        self, pair: Pair, timeframe: Timeframe, candles: Sequence[Candle]
    ) -> UpsertResult:
        return self.upsert(pair, timeframe, candles_to_frame(candles))
