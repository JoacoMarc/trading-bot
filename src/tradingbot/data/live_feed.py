"""`LiveFeed`: `Bar`s cerrados desde el exchange, mismo contrato que `HistoricalFeed` (ADR-0011).

- Bootstrap por REST: `warmup` velas cerradas por par antes de la primera que se va a emitir.
  Una vela está cerrada si `open_time + tf ≤ now_exchange − close_delay`; la que está en formación
  se descarta. Con `resume_from` (última vela procesada antes de un reinicio) las velas cerradas
  que quedaron sin procesar se emiten primero como `Bar`s de **reposición** (`replay=True`).
- Cierre de vela: el reloj es el del exchange (`source.now_ms()`). A `close_time + close_delay`
  se pide la vela y el cierre de `t` se confirma **por la aparición de la vela `t+1`**, nunca por
  el reloj local. Si no aparece se reintenta cada `retry_s` hasta `retry_window_s`; después el
  `Bar` sale con los pares confirmados (el resto queda como hueco, con evento). Si ningún par
  confirma, se sigue esperando: una vela no se saltea. Errores del exchange → backoff exponencial.
- `stop()` corta la iteración en el próximo despertar (shutdown ordenado).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from tradingbot.domain.candle import Bar, Candle
from tradingbot.domain.errors import ExchangeError, InsufficientWarmup
from tradingbot.domain.pair import Pair
from tradingbot.domain.timeframe import Timeframe

log = logging.getLogger(__name__)

AsyncSleep = Callable[[float], Awaitable[None]]

FEED_MISSING_PAIR = "feed_missing_pair"
FEED_RETRY = "feed_retry"
FEED_REPLAY = "feed_replay"
FEED_LATE = "feed_late"


class LiveSource(Protocol):
    """Lo que el feed necesita del exchange (`BinanceExchange` lo cumple; los tests lo fingen)."""

    def now_ms(self) -> int: ...

    def fetch_ohlcv_page(
        self, pair: Pair, timeframe: Timeframe, since_ms: int, limit: int = 1000
    ) -> list[Candle]: ...


@dataclass(frozen=True, slots=True)
class FeedEvent:
    ts: int
    kind: str
    pair: Pair | None = None
    detail: str = ""


def _log_event(event: FeedEvent) -> None:
    log.info("%s %s %s", event.kind, "" if event.pair is None else event.pair.symbol, event.detail)


class LiveFeed:
    def __init__(
        self,
        source: LiveSource,
        pairs: Sequence[Pair],
        timeframe: Timeframe,
        warmup: int,
        *,
        resume_from: int | None = None,
        close_delay_ms: int = 3_000,
        retry_s: float = 2.0,
        retry_window_s: float = 60.0,
        backoff_max_s: float = 60.0,
        wait_chunk_s: float = 10.0,
        page_limit: int = 1000,
        sleep: AsyncSleep = asyncio.sleep,
        on_event: Callable[[FeedEvent], None] | None = None,
    ) -> None:
        if not pairs:
            msg = "LiveFeed necesita al menos un par"
            raise ValueError(msg)
        if warmup < 0:
            msg = f"warmup negativo: {warmup}"
            raise ValueError(msg)
        if resume_from is not None:
            timeframe.check_aligned(resume_from)
        self._source = source
        self._pairs = tuple(sorted(set(pairs)))
        self._timeframe = timeframe
        self._warmup = warmup
        self._resume_from = resume_from
        self._close_delay_ms = close_delay_ms
        self._retry_s = retry_s
        self._retry_window_ms = int(retry_window_s * 1000)
        self._backoff_max_s = backoff_max_s
        self._wait_chunk_s = wait_chunk_s
        self._page_limit = page_limit
        self._sleep = sleep
        self._on_event = on_event or _log_event
        self._warmup_candles: dict[Pair, list[Candle]] = {}
        self._replay: list[Bar] = []
        self._last_open_time: int | None = None
        self._stopped = False
        self._bootstrapped = False

    # ------------------------------------------------------------- API (MarketFeed)

    @property
    def timeframe(self) -> Timeframe:
        return self._timeframe

    @property
    def pairs(self) -> tuple[Pair, ...]:
        return self._pairs

    @property
    def last_open_time(self) -> int | None:
        """`open_time` del último `Bar` emitido (o del último cerrado al bootstrap)."""
        return self._last_open_time

    @property
    def replay_pending(self) -> int:
        return len(self._replay)

    def stop(self) -> None:
        """Termina la iteración en el próximo despertar (shutdown ordenado)."""
        self._stopped = True

    def _stop_requested(self) -> bool:
        return self._stopped  # vía método: mypy no estrecha el atributo entre awaits

    def warmup_bars(self) -> list[Bar]:
        self._ensure_bootstrap()
        times: set[int] = set()
        for candles in self._warmup_candles.values():
            times.update(c.open_time for c in candles)
        by_pair = {p: {c.open_time: c for c in cs} for p, cs in self._warmup_candles.items()}
        bars: list[Bar] = []
        for t in sorted(times):
            at_t = {p: by_time[t] for p, by_time in by_pair.items() if t in by_time}
            bars.append(Bar(timeframe=self._timeframe, open_time=t, candles=at_t))
        return bars

    def warmup_candles(self, pair: Pair) -> list[Candle]:
        self._ensure_bootstrap()
        return list(self._warmup_candles[pair])

    # ------------------------------------------------------------- bootstrap

    def _ensure_bootstrap(self) -> None:
        if not self._bootstrapped:
            self.bootstrap()

    def _closed_cutoff(self) -> int:
        """Primer `open_time` que todavía no se considera cerrado."""
        now = self._source.now_ms()
        return self._timeframe.floor(max(now - self._close_delay_ms, 0))

    def bootstrap(self) -> None:
        """Carga warmup (y velas de reposición si hay `resume_from`). Idempotente."""
        tf = self._timeframe.ms
        cutoff = self._closed_cutoff()
        last_closed = cutoff - tf
        first_emit = last_closed + tf
        if self._resume_from is not None and self._resume_from + tf <= last_closed:
            first_emit = self._resume_from + tf
        since = first_emit - self._warmup * tf
        replay_by_time: dict[int, dict[Pair, Candle]] = {}
        for pair in self._pairs:
            candles = self._fetch_closed(pair, since, cutoff)
            warm = [c for c in candles if c.open_time < first_emit]
            if len(warm) < self._warmup:
                msg = (
                    f"{pair} {self._timeframe.value}: warmup de {self._warmup} velas antes de "
                    f"{first_emit}, el exchange devolvió {len(warm)}"
                )
                raise InsufficientWarmup(msg)
            self._warmup_candles[pair] = warm[len(warm) - self._warmup :] if self._warmup else []
            for candle in candles:
                if first_emit <= candle.open_time <= last_closed:
                    replay_by_time.setdefault(candle.open_time, {})[pair] = candle
        self._replay = [
            Bar(timeframe=self._timeframe, open_time=t, candles=replay_by_time[t], replay=True)
            for t in sorted(replay_by_time)
        ]
        self._last_open_time = last_closed
        self._bootstrapped = True
        if self._replay:
            self._on_event(
                FeedEvent(
                    ts=self._source.now_ms(),
                    kind=FEED_REPLAY,
                    detail=f"{len(self._replay)} velas cerradas sin procesar desde "
                    f"{self._replay[0].open_time} hasta {self._replay[-1].open_time}",
                )
            )

    def _fetch_closed(self, pair: Pair, since_ms: int, cutoff_ms: int) -> list[Candle]:
        """Velas cerradas de `[since_ms, cutoff_ms)`, paginadas, deduplicadas y ordenadas."""
        tf = self._timeframe.ms
        result: dict[int, Candle] = {}
        cursor = max(since_ms, 0)
        while cursor < cutoff_ms:
            page = self._source.fetch_ohlcv_page(pair, self._timeframe, cursor, self._page_limit)
            if not page:
                break
            for candle in page:
                if candle.open_time < cutoff_ms:
                    result[candle.open_time] = candle
            if len(page) < self._page_limit:
                break
            cursor = page[-1].open_time + tf
        return [result[t] for t in sorted(result)]

    # ------------------------------------------------------------- iteración

    async def __aiter__(self) -> AsyncIterator[Bar]:
        self._ensure_bootstrap()
        while self._replay and not self._stopped:
            bar = self._replay.pop(0)
            self._last_open_time = bar.open_time
            yield bar
        tf = self._timeframe.ms
        while not self._stopped:
            assert self._last_open_time is not None
            next_open = self._last_open_time + tf
            target = next_open + tf + self._close_delay_ms
            now = self._source.now_ms()
            if now < target:
                await self._pause((target - now) / 1000)
                continue
            collected = await self._collect(next_open)
            if self._stop_requested():
                return
            # Sin vela en ningún par (hueco real ya avisado): la vela se saltea, el feed sigue.
            self._last_open_time = next_open
            if collected is not None:
                yield collected

    async def _pause(self, seconds: float) -> None:
        """Duerme en tramos de `wait_chunk_s` para que `stop()` corte en segundos, no en horas."""
        remaining = seconds
        while remaining > 0 and not self._stopped:
            chunk = min(remaining, self._wait_chunk_s)
            await self._sleep(chunk)
            remaining -= chunk

    async def _collect(self, open_time: int) -> Bar | None:
        """Vela `open_time` de cada par, confirmada por una vela posterior (o por reloj)."""
        deadline = self._source.now_ms() + self._retry_window_ms
        confirmed: dict[Pair, Candle] = {}
        pending = set(self._pairs)
        backoff = self._retry_s
        late_reported = False
        while pending and not self._stopped:
            failed = False
            for pair in sorted(pending):
                try:
                    page = self._source.fetch_ohlcv_page(pair, self._timeframe, open_time, 2)
                except ExchangeError as exc:
                    failed = True
                    self._on_event(
                        FeedEvent(
                            self._source.now_ms(),
                            FEED_RETRY,
                            pair,
                            f"{exc}; backoff {backoff:.0f} s",
                        )
                    )
                    break
                by_time = {c.open_time: c for c in page}
                candle = by_time.get(open_time)
                # Cierre confirmado por cualquier vela posterior (t+1, o t+2 si Binance salteó
                # t+1 por mantenimiento). Sin vela posterior, tras la ventana se acepta la vela
                # si está: el reloj del exchange ya la dio por cerrada hace > retry_window.
                if not any(t > open_time for t in by_time):
                    if candle is not None and self._source.now_ms() >= deadline:
                        confirmed[pair] = candle
                        pending.discard(pair)
                        self._on_event(
                            FeedEvent(
                                self._source.now_ms(),
                                FEED_LATE,
                                pair,
                                f"vela {open_time} aceptada por reloj: la siguiente no apareció en "
                                f"{self._retry_window_ms // 1000} s",
                            )
                        )
                    continue
                if candle is None:
                    self._on_event(
                        FeedEvent(
                            self._source.now_ms(),
                            FEED_MISSING_PAIR,
                            pair,
                            f"sin vela {open_time} aunque ya existe la siguiente",
                        )
                    )
                else:
                    confirmed[pair] = candle
                pending.discard(pair)
            if not pending:
                break
            now = self._source.now_ms()
            if confirmed and now >= deadline:
                for pair in sorted(pending):
                    self._on_event(
                        FeedEvent(
                            now,
                            FEED_MISSING_PAIR,
                            pair,
                            f"vela {open_time} sin confirmar tras "
                            f"{self._retry_window_ms // 1000} s",
                        )
                    )
                break
            if not confirmed and now >= deadline and not late_reported:
                late_reported = True
                self._on_event(
                    FeedEvent(now, FEED_LATE, None, f"ningún par confirmó la vela {open_time}")
                )
            await self._pause(backoff)
            backoff = min(backoff * 2, self._backoff_max_s) if failed else self._retry_s
        if self._stopped or not confirmed:
            return None
        return Bar(timeframe=self._timeframe, open_time=open_time, candles=confirmed)
