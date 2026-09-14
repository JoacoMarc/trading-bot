"""`LiveFeed` (ADR-0011): bootstrap, cierre confirmado por t+1, reintentos, huecos, reposición."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.factories import BTC, ETH, H4_MS, T0, make_series
from tradingbot.data import (
    FEED_LATE,
    FEED_MISSING_PAIR,
    FEED_REPLAY,
    FEED_RETRY,
    FeedEvent,
    LiveFeed,
    MarketFeed,
)
from tradingbot.domain import Bar, Candle, InsufficientWarmup, Pair, Timeframe
from tradingbot.domain.errors import ExchangeUnavailable

H4 = Timeframe.H4


class FakeSource:
    """Exchange falso: reloj propio; una vela es visible desde su `open_time` + retardo."""

    def __init__(
        self,
        candles: dict[Pair, Sequence[Candle]],
        now_ms: int,
        *,
        publish_lag_ms: int = 0,
        failures: list[Exception] | None = None,
    ) -> None:
        self.candles = {p: sorted(cs, key=lambda c: c.open_time) for p, cs in candles.items()}
        self.now = now_ms
        self.publish_lag_ms = publish_lag_ms
        self.failures = list(failures or [])
        self.calls: list[tuple[str, int, int]] = []
        self.sleeps: list[float] = []

    def now_ms(self) -> int:
        return self.now

    def fetch_ohlcv_page(
        self, pair: Pair, timeframe: Timeframe, since_ms: int, limit: int = 1000
    ) -> list[Candle]:
        self.calls.append((pair.symbol, since_ms, limit))
        if self.failures:
            raise self.failures.pop(0)
        visible = [
            c
            for c in self.candles.get(pair, [])
            if c.open_time >= since_ms and c.open_time + self.publish_lag_ms <= self.now
        ]
        return visible[:limit]

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += int(seconds * 1000)


def make_feed(
    source: FakeSource,
    pairs: Sequence[Pair],
    warmup: int = 3,
    **kwargs: object,
) -> LiveFeed:
    events: list[FeedEvent] = []
    feed = LiveFeed(
        source,
        pairs,
        H4,
        warmup,
        sleep=source.sleep,
        on_event=events.append,
        **kwargs,  # type: ignore[arg-type]
    )
    feed.events = events  # type: ignore[attr-defined]
    return feed


async def take(feed: LiveFeed, n: int) -> list[Bar]:
    bars: list[Bar] = []
    async for bar in feed:
        bars.append(bar)
        if len(bars) == n:
            feed.stop()
    return bars


def events_of(feed: LiveFeed) -> list[FeedEvent]:
    return feed.events  # type: ignore[attr-defined, no-any-return]


async def test_bootstrap_warmup_then_live_bars_confirmed_by_next_candle() -> None:
    btc = make_series(pair=BTC, n=14)
    eth = make_series(pair=ETH, n=14, base_price=10)
    # Ahora = 5 min después de abrir la vela 10: la 9 es la última cerrada, la 10 está en formación.
    source = FakeSource({BTC: btc, ETH: eth}, now_ms=T0 + 10 * H4_MS + 300_000)
    feed: MarketFeed = make_feed(source, [ETH, BTC], warmup=3)
    assert feed.pairs == (BTC, ETH)
    warm = feed.warmup_bars()
    assert [b.open_time for b in warm] == [T0 + i * H4_MS for i in (7, 8, 9)]
    assert all(b.pairs == (BTC, ETH) for b in warm)
    assert all(not b.replay for b in warm)

    bars = await take(feed, 2)  # type: ignore[arg-type]
    assert [b.open_time for b in bars] == [T0 + 10 * H4_MS, T0 + 11 * H4_MS]
    assert all(not b.replay for b in bars)
    assert bars[0].get(BTC) == btc[10]
    # La vela 10 se pidió recién a close + 3 s, y se confirmó porque la 11 ya existía.
    first_live_call = next(c for c in source.calls if c[1] == T0 + 10 * H4_MS and c[2] == 2)
    assert first_live_call[0] == "BTC/USDT"
    assert source.sleeps  # esperó hasta el cierre en tramos


async def test_resume_emits_replay_bars_before_live() -> None:
    btc = make_series(pair=BTC, n=14)
    source = FakeSource({BTC: btc}, now_ms=T0 + 10 * H4_MS + 300_000)
    feed = make_feed(source, [BTC], warmup=2, resume_from=T0 + 6 * H4_MS)
    warm = feed.warmup_bars()
    assert [b.open_time for b in warm] == [
        T0 + 5 * H4_MS,
        T0 + 6 * H4_MS,
    ]  # antes de la primera repuesta
    assert feed.replay_pending == 3  # velas 7, 8 y 9 quedaron sin procesar
    bars = await take(feed, 4)
    assert [b.open_time for b in bars] == [T0 + i * H4_MS for i in (7, 8, 9, 10)]
    assert [b.replay for b in bars] == [True, True, True, False]
    assert [e.kind for e in events_of(feed)] == [FEED_REPLAY]
    assert feed.last_open_time == T0 + 10 * H4_MS


async def test_resume_from_recent_bar_has_no_replay() -> None:
    source = FakeSource({BTC: make_series(pair=BTC, n=14)}, now_ms=T0 + 10 * H4_MS + 300_000)
    feed = make_feed(source, [BTC], warmup=2, resume_from=T0 + 9 * H4_MS)
    feed.bootstrap()
    assert feed.replay_pending == 0
    assert feed.last_open_time == T0 + 9 * H4_MS


async def test_waits_for_next_candle_and_retries_every_two_seconds() -> None:
    # La vela t+1 tarda 7 s en aparecer en el exchange: a close + 3 s todavía no está.
    source = FakeSource(
        {BTC: make_series(pair=BTC, n=13)}, now_ms=T0 + 10 * H4_MS + 60_000, publish_lag_ms=7_000
    )
    feed = make_feed(source, [BTC], warmup=1)
    bars = await take(feed, 1)
    assert bars[0].open_time == T0 + 10 * H4_MS
    assert 2.0 in source.sleeps  # reintentos de 2 s hasta ver la vela 11
    assert source.now >= T0 + 11 * H4_MS + 7_000


async def test_partial_bar_after_retry_window_and_missing_pair_event() -> None:
    btc = make_series(pair=BTC, n=13)
    eth = make_series(pair=ETH, n=13, base_price=10, skip=frozenset({10}))  # ETH sin la vela 10
    source = FakeSource({BTC: btc, ETH: eth}, now_ms=T0 + 10 * H4_MS + 60_000)
    feed = make_feed(source, [BTC, ETH], warmup=1)
    bars = await take(feed, 1)
    assert bars[0].pairs == (BTC,)  # ETH ya tiene la 11: su hueco en la 10 es real
    kinds = [(e.kind, e.pair) for e in events_of(feed)]
    assert (FEED_MISSING_PAIR, ETH) in kinds


async def test_slow_pair_is_accepted_by_clock_after_the_window() -> None:
    btc = make_series(pair=BTC, n=13)
    eth = make_series(pair=ETH, n=11, base_price=10)  # ETH nunca publica la vela 11
    source = FakeSource({BTC: btc, ETH: eth}, now_ms=T0 + 10 * H4_MS + 60_000)
    feed = make_feed(source, [BTC, ETH], warmup=1, retry_window_s=10.0)
    bars = await take(feed, 1)
    assert bars[0].pairs == (BTC, ETH)  # la vela 10 de ETH existe: cerrada por reloj
    assert bars[0].open_time == T0 + 10 * H4_MS
    late = next(e for e in events_of(feed) if e.kind == FEED_LATE)
    assert late.pair == ETH


async def test_pair_without_the_candle_is_dropped_after_window() -> None:
    btc = make_series(pair=BTC, n=13)
    eth = make_series(pair=ETH, n=10, base_price=10)  # ETH no tiene ni la 10 ni la 11
    source = FakeSource({BTC: btc, ETH: eth}, now_ms=T0 + 10 * H4_MS + 60_000)
    feed = make_feed(source, [BTC, ETH], warmup=1, retry_window_s=10.0)
    bars = await take(feed, 1)
    assert bars[0].pairs == (BTC,)
    detail = next(e for e in events_of(feed) if e.kind == FEED_MISSING_PAIR).detail
    assert "sin confirmar" in detail


async def test_close_is_confirmed_by_any_later_candle_when_binance_skips_one() -> None:
    # Mantenimiento: no existe la vela 11, pero la 12 sí -> la 10 se confirma igual.
    btc = make_series(pair=BTC, n=14, skip=frozenset({11}))
    source = FakeSource({BTC: btc}, now_ms=T0 + 10 * H4_MS + 60_000)
    feed = make_feed(source, [BTC], warmup=1, retry_window_s=10.0)
    bars = await take(feed, 2)
    # La 10 se acepta por reloj pasada la ventana (no existe la 11 que la confirme) y la 11, que
    # no existe, se saltea con evento: el feed sigue con la 12 en vez de terminar.
    assert [b.open_time for b in bars] == [T0 + 10 * H4_MS, T0 + 12 * H4_MS]
    kinds = [e.kind for e in events_of(feed)]
    assert FEED_LATE in kinds
    assert FEED_MISSING_PAIR in kinds


async def test_exchange_errors_back_off_and_recover() -> None:
    # Un minuto antes de que cierre la vela 10; las fallas llegan al pedirla tras el cierre.
    source = FakeSource({BTC: make_series(pair=BTC, n=13)}, now_ms=T0 + 11 * H4_MS - 60_000)
    feed = make_feed(source, [BTC], warmup=1)
    feed.bootstrap()  # las fallas se inyectan después del bootstrap
    source.failures = [ExchangeUnavailable("timeout"), ExchangeUnavailable("timeout")]
    bars = await take(feed, 1)
    assert bars[0].open_time == T0 + 10 * H4_MS
    retries = [e for e in events_of(feed) if e.kind == FEED_RETRY]
    assert len(retries) == 2
    assert source.sleeps[-2:] == [2.0, 4.0]  # backoff exponencial entre fallas


def test_insufficient_warmup_is_an_error() -> None:
    source = FakeSource({BTC: make_series(pair=BTC, n=4)}, now_ms=T0 + 3 * H4_MS + 60_000)
    feed = make_feed(source, [BTC], warmup=5)
    with pytest.raises(InsufficientWarmup, match="warmup de 5"):
        feed.bootstrap()


def test_bootstrap_paginates_long_warmups() -> None:
    source = FakeSource({BTC: make_series(pair=BTC, n=30)}, now_ms=T0 + 29 * H4_MS + 60_000)
    feed = make_feed(source, [BTC], warmup=25, page_limit=10)
    warm = feed.warmup_bars()
    assert len(warm) == 25
    assert warm[-1].open_time == T0 + 28 * H4_MS
    assert len([c for c in source.calls if c[2] == 10]) >= 3  # varias páginas de 10


async def test_stop_during_a_long_wait_returns_within_one_chunk() -> None:
    source = FakeSource({BTC: make_series(pair=BTC, n=13)}, now_ms=T0 + 10 * H4_MS + 60_000)
    feed = make_feed(source, [BTC], warmup=1, wait_chunk_s=5.0)
    feed.bootstrap()

    async def stop_after_first_sleep(seconds: float) -> None:
        source.sleeps.append(seconds)
        source.now += int(seconds * 1000)
        feed.stop()

    feed._sleep = stop_after_first_sleep
    bars = [bar async for bar in feed]
    assert bars == []
    assert source.sleeps == [5.0]  # un solo tramo: `stop()` cortó la espera de 4 h
