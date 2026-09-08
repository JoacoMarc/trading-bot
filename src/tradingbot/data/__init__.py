"""Capa de datos: store parquet, descarga incremental, calidad y feeds que emiten `Bar`."""

from tradingbot.data.downloader import (
    DEFAULT_CLOSE_SAFETY_MS,
    Downloader,
    DownloadResult,
    GapFillResult,
    closed_cutoff_ms,
    drop_forming,
)
from tradingbot.data.feeds import HistoricalFeed, MarketFeed
from tradingbot.data.quality import Gap, GapRegistry, QualityReport, check_frame, find_gaps
from tradingbot.data.store import (
    COLUMNS,
    OHLCV_SCHEMA,
    DatasetInfo,
    ParquetStore,
    UpsertResult,
    candles_to_frame,
    frame_to_candles,
    iter_rows,
    read_parquet,
    read_parquet_metadata,
    validate_frame,
    write_parquet,
)

__all__ = [
    "COLUMNS",
    "DEFAULT_CLOSE_SAFETY_MS",
    "OHLCV_SCHEMA",
    "DatasetInfo",
    "DownloadResult",
    "Downloader",
    "Gap",
    "GapFillResult",
    "GapRegistry",
    "HistoricalFeed",
    "MarketFeed",
    "ParquetStore",
    "QualityReport",
    "UpsertResult",
    "candles_to_frame",
    "check_frame",
    "closed_cutoff_ms",
    "drop_forming",
    "find_gaps",
    "frame_to_candles",
    "iter_rows",
    "read_parquet",
    "read_parquet_metadata",
    "validate_frame",
    "write_parquet",
]
