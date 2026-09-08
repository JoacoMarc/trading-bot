"""Descarga incremental de OHLCV al `ParquetStore`.

Reglas:
- **Nunca se guarda la vela en formación**: una vela con `open_time` está cerrada solo si
  `open_time + tf_ms ≤ hora_del_exchange − margen`. Se usa el reloj de Binance
  (`BinanceExchange.now_ms`), no el local, y un margen de seguridad (`close_safety_ms`) cubre el
  error del offset cacheado y el retardo con que Binance publica la vela cerrada.
- **Incremental idempotente**: si ya hay datos, se re-pide desde la última vela guardada
  **inclusive** (por si quedó guardada con datos parciales) y se hace upsert por `open_time`.
  Correr dos veces seguidas no cambia el archivo. La serie guardada se mantiene **contigua**: un
  `since` posterior a la última vela guardada no abre un hueco, se continúa desde ella.
- Si `since` es anterior a la primera vela guardada, también se rellena hacia atrás.
- **Progreso persistente**: se hace upsert cada `flush_pages` páginas; un corte a mitad de una
  descarga inicial conserva lo bajado y la corrida siguiente continúa desde ahí.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from tradingbot.data.quality import Gap
from tradingbot.data.store import ParquetStore, candles_to_frame
from tradingbot.domain.candle import Candle
from tradingbot.domain.pair import Pair
from tradingbot.domain.timeframe import Timeframe
from tradingbot.exchange.binance import OHLCV_PAGE_LIMIT, BinanceExchange

log = logging.getLogger(__name__)

DEFAULT_CLOSE_SAFETY_MS = 2_000


@dataclass(frozen=True, slots=True)
class DownloadResult:
    pair: Pair
    timeframe: Timeframe
    since_ms: int
    until_ms: int
    fetched: int
    # El corte a velas cerradas ya se pide al exchange (`until_ms`); este contador registra lo que
    # el filtro defensivo descartó igual (normalmente 0).
    discarded_forming: int
    added: int
    updated: int
    total_rows: int
    first_open_time: int | None
    last_open_time: int | None

    @property
    def changed(self) -> bool:
        return self.added > 0 or self.updated > 0


@dataclass(frozen=True, slots=True)
class GapFillResult:
    """Resultado de verificar un hueco contra el exchange."""

    gap: Gap
    filled: int  # velas que el exchange sí tenía y se guardaron

    @property
    def confirmed_empty(self) -> bool:
        return self.filled == 0


def closed_cutoff_ms(timeframe: Timeframe, exchange_now_ms: int, safety_ms: int = 0) -> int:
    """Primer `open_time` que todavía **no** se considera cerrado (corte exclusivo).

    Una vela está cerrada si `open_time + tf_ms ≤ now − safety`; el mayor `open_time` cerrado es
    `floor(now − safety) − tf_ms`, así que el corte exclusivo es `floor(now − safety)`.
    """
    return timeframe.floor(max(exchange_now_ms - safety_ms, 0))


def drop_forming(
    candles: Sequence[Candle], timeframe: Timeframe, exchange_now_ms: int, safety_ms: int = 0
) -> tuple[list[Candle], int]:
    """Separa las velas cerradas de la vela en formación (y de cualquier futuro espurio)."""
    cutoff = closed_cutoff_ms(timeframe, exchange_now_ms, safety_ms)
    kept = [c for c in candles if c.open_time < cutoff]
    return kept, len(candles) - len(kept)


class Downloader:
    """Baja velas cerradas del exchange y las persiste de forma incremental."""

    def __init__(
        self,
        exchange: BinanceExchange,
        store: ParquetStore,
        *,
        page_limit: int = OHLCV_PAGE_LIMIT,
        flush_pages: int = 10,
        close_safety_ms: int = DEFAULT_CLOSE_SAFETY_MS,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        if flush_pages < 1:
            msg = f"flush_pages debe ser >= 1, recibido {flush_pages}"
            raise ValueError(msg)
        self._exchange = exchange
        self._store = store
        self._page_limit = page_limit
        self._flush_pages = flush_pages
        self._close_safety_ms = close_safety_ms
        self._progress = progress

    def _report(self, message: str) -> None:
        log.info(message)
        if self._progress is not None:
            self._progress(message)

    def closed_until_ms(self, timeframe: Timeframe) -> int:
        """Corte exclusivo de velas cerradas según el reloj del exchange y el margen."""
        return closed_cutoff_ms(timeframe, self._exchange.now_ms(), self._close_safety_ms)

    def plan_ranges(
        self, pair: Pair, timeframe: Timeframe, since_ms: int, until_ms: int
    ) -> list[tuple[int, int]]:
        """Rangos `[a, b)` a pedir según lo que ya hay guardado, sin abrir huecos."""
        info = self._store.info(pair, timeframe)
        if info is None:
            return [(since_ms, until_ms)]
        ranges: list[tuple[int, int]] = []
        if since_ms < info.first_open_time:
            ranges.append((since_ms, min(info.first_open_time, until_ms)))
        if since_ms > info.last_open_time:
            log.warning(
                "%s %s: since %d posterior a la última vela guardada %d; se continúa desde ella "
                "para no abrir un hueco",
                pair,
                timeframe.value,
                since_ms,
                info.last_open_time,
            )
        # Última vela guardada inclusive: si quedó incompleta, el upsert la corrige.
        if info.last_open_time < until_ms:
            ranges.append((info.last_open_time, until_ms))
        return ranges

    def _fetch_range(
        self, pair: Pair, timeframe: Timeframe, start: int, end: int
    ) -> tuple[int, int, int, int]:
        """Baja `[start, end)` persistiendo cada `flush_pages`.

        Devuelve `(fetched, dropped, added, updated)`.
        """
        fetched = dropped = added = updated = 0
        buffer: list[Candle] = []
        pages = 0

        def flush() -> None:
            nonlocal added, updated
            if not buffer:
                return
            result = self._store.upsert(pair, timeframe, candles_to_frame(buffer))
            added += result.added
            updated += result.updated
            buffer.clear()

        try:
            for page in self._exchange.iter_ohlcv_pages(
                pair, timeframe, start, end, page_limit=self._page_limit
            ):
                kept, gone = drop_forming(
                    page, timeframe, self._exchange.now_ms(), self._close_safety_ms
                )
                fetched += len(kept)
                dropped += gone
                buffer.extend(kept)
                pages += 1
                if pages % self._flush_pages == 0:
                    flush()
                    self._report(
                        f"{pair} {timeframe.value}: {fetched} velas hasta "
                        f"{buffer_last(kept) or start} guardadas"
                    )
        finally:
            flush()  # ante un error, lo ya bajado queda persistido
        return fetched, dropped, added, updated

    def download(
        self, pair: Pair, timeframe: Timeframe, since_ms: int, until_ms: int | None = None
    ) -> DownloadResult:
        """Descarga `[since_ms, until_ms)` acotado a velas cerradas y hace upsert."""
        timeframe.check_aligned(since_ms)
        cutoff = self.closed_until_ms(timeframe)
        effective_until = cutoff if until_ms is None else min(until_ms, cutoff)

        fetched = discarded = added = updated = 0
        for start, end in self.plan_ranges(pair, timeframe, since_ms, effective_until):
            if start >= end:
                continue
            f, d, a, u = self._fetch_range(pair, timeframe, start, end)
            fetched += f
            discarded += d
            added += a
            updated += u
            self._report(f"{pair} {timeframe.value}: {f} velas cerradas recibidas [{start}, {end})")

        info = self._store.info(pair, timeframe)
        return DownloadResult(
            pair=pair,
            timeframe=timeframe,
            since_ms=since_ms,
            until_ms=effective_until,
            fetched=fetched,
            discarded_forming=discarded,
            added=added,
            updated=updated,
            total_rows=info.rows if info else 0,
            first_open_time=info.first_open_time if info else None,
            last_open_time=info.last_open_time if info else None,
        )

    def download_many(
        self,
        pairs: Sequence[Pair],
        timeframes: Sequence[Timeframe],
        since_ms: int,
        until_ms: int | None = None,
    ) -> list[DownloadResult]:
        """Descarga todos los pares × timeframes en orden determinístico."""
        results: list[DownloadResult] = []
        for pair in sorted(pairs):
            for timeframe in sorted(timeframes, key=lambda tf: tf.ms):
                results.append(self.download(pair, timeframe, since_ms, until_ms))
        return results

    def fill_gaps(
        self, pair: Pair, timeframe: Timeframe, gaps: Sequence[Gap]
    ) -> list[GapFillResult]:
        """Re-pide cada hueco al exchange: lo que exista se guarda; lo vacío es un hueco real."""
        results: list[GapFillResult] = []
        for gap in gaps:
            candles = self._exchange.fetch_ohlcv(
                pair,
                timeframe,
                gap.start_ms,
                gap.end_ms + timeframe.ms,
                page_limit=self._page_limit,
            )
            kept, _ = drop_forming(
                candles, timeframe, self._exchange.now_ms(), self._close_safety_ms
            )
            if kept:
                self._store.upsert(pair, timeframe, candles_to_frame(kept))
            results.append(GapFillResult(gap=gap, filled=len(kept)))
        return results


def buffer_last(candles: Sequence[Candle]) -> int | None:
    return candles[-1].open_time if candles else None
