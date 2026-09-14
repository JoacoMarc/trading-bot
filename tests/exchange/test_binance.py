"""Adapter de Binance con cliente falso: parsing, retry, mapeo de errores, paginado, reloj."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import ccxt
import pytest

from tests.exchange.fake_ccxt import EXCHANGE_INFO, FakeCcxt, binance_market, ohlcv_rows
from tests.factories import BTC, ETH, H4_MS, T0
from tradingbot.domain import (
    AuthError,
    ExchangeError,
    ExchangeUnavailable,
    InsufficientFunds,
    InvalidOrder,
    Pair,
    RateLimited,
    Timeframe,
)
from tradingbot.exchange import (
    OHLCV_PAGE_LIMIT,
    BinanceExchange,
    MarketInfo,
    build_markets_snapshot,
    is_ip_ban,
    load_markets_snapshot,
    map_ccxt_error,
    parse_kline_row,
    parse_market,
    parse_rate_limits,
    redact,
    save_markets_snapshot,
)


def make_exchange(
    client: FakeCcxt, max_retries: int = 5, rate_limit_min_wait_s: float = 5.0
) -> tuple[BinanceExchange, list[float]]:
    sleeps: list[float] = []
    exchange = BinanceExchange(
        client,
        sleep=sleeps.append,
        backoff_base_s=1.0,
        backoff_max_s=8.0,
        max_retries=max_retries,
        rate_limit_min_wait_s=rate_limit_min_wait_s,
    )
    return exchange, sleeps


# --------------------------------------------------------------------------- mercados


def test_parse_market_reads_exact_strings_from_filters() -> None:
    market = parse_market(binance_market("BTC", tick="0.01000000", step="0.00001000"))
    assert market is not None
    assert market.pair == BTC
    assert market.tick_size == Decimal("0.01")
    assert market.step_size == Decimal("0.00001")
    assert market.min_qty == Decimal("0.00001")
    assert market.max_qty == Decimal("9000")
    assert market.min_notional == Decimal("5")
    assert market.active
    assert market.supports_native_stop()


def test_parse_market_falls_back_to_ccxt_precision_without_filters() -> None:
    market = parse_market(binance_market("ETH", tick="0.01", step="0.0001", with_filters=False))
    assert market is not None
    assert market.tick_size == Decimal("0.01")
    assert market.step_size == Decimal("0.0001")
    assert market.min_notional == Decimal("5")


def test_parse_market_skips_non_spot_and_non_usdt() -> None:
    assert parse_market(binance_market("BTC", quote="BUSD")) is None
    assert parse_market(binance_market("BTC", spot=False)) is None


def test_parse_market_accepts_single_letter_base_and_skips_unrepresentable() -> None:
    # Binance lista `T/USDT` (Threshold); un símbolo con caracteres raros no debe tumbar
    # la carga de todo el universo.
    single = parse_market(binance_market("T"))
    assert single is not None
    assert single.pair.base == "T"
    assert parse_market(binance_market("AB_C")) is None


def test_parse_market_inactive_when_status_not_trading() -> None:
    market = parse_market(binance_market("XYZ", status="BREAK"))
    assert market is not None
    assert not market.active


def test_market_info_filters_and_quantization() -> None:
    market = MarketInfo(
        pair=BTC,
        tick_size=Decimal("0.01"),
        step_size=Decimal("0.00001"),
        min_qty=Decimal("0.00001"),
        min_notional=Decimal("5"),
    )
    assert market.quantize_qty(Decimal("0.123456789")) == Decimal("0.12345")
    assert market.quantize_price(Decimal("27123.456")) == Decimal("27123.46")
    assert market.meets_filters(Decimal("27000"), Decimal("0.001"))
    assert not market.meets_filters(Decimal("27000"), Decimal("0.0001"))  # notional 2.7 < 5
    assert not market.meets_filters(Decimal("27000"), Decimal("0.000001"))  # < min_qty


def test_load_markets_caches_until_reload() -> None:
    client = FakeCcxt(
        markets={"BTC/USDT": binance_market("BTC"), "ETH/BTC": binance_market("ETH", quote="BTC")}
    )
    exchange, _ = make_exchange(client)
    markets = exchange.load_markets()
    assert set(markets) == {BTC}
    exchange.load_markets()
    assert client.count("load_markets") == 1
    exchange.load_markets(reload=True)
    assert client.count("load_markets") == 2
    assert exchange.market(BTC).tick_size == Decimal("0.01")
    with pytest.raises(ExchangeError, match="no está listado"):
        exchange.market(ETH)


def test_rate_limits_from_exchange_info() -> None:
    limits = parse_rate_limits(EXCHANGE_INFO)
    assert limits.request_weight_per_minute == 6000
    assert limits.orders_per_10s == 100
    assert limits.orders_per_day == 200_000
    assert parse_rate_limits({}).request_weight_per_minute == 6000  # default


# --------------------------------------------------------------------------- errores y retry


@pytest.mark.parametrize(
    ("ccxt_error", "domain_error"),
    [
        (ccxt.AuthenticationError("bad key"), AuthError),
        (ccxt.PermissionDenied("no perms"), AuthError),
        (ccxt.InsufficientFunds("poor"), InsufficientFunds),
        (ccxt.InvalidOrder("filter"), InvalidOrder),
        (ccxt.OrderNotFound("gone"), InvalidOrder),
        (ccxt.BadSymbol("FOO/USDT"), InvalidOrder),
        (ccxt.RateLimitExceeded("429"), RateLimited),
        (ccxt.DDoSProtection("418"), RateLimited),
        (ccxt.RequestTimeout("slow"), ExchangeUnavailable),
        (ccxt.ExchangeNotAvailable("503"), ExchangeUnavailable),
        (ccxt.OnMaintenance("maint"), ExchangeUnavailable),
        (ccxt.NetworkError("dns"), ExchangeUnavailable),
        (ccxt.ExchangeError("otro"), ExchangeError),
    ],
)
def test_map_ccxt_error(ccxt_error: Exception, domain_error: type[ExchangeError]) -> None:
    mapped = map_ccxt_error(ccxt_error)
    assert type(mapped) is domain_error
    assert mapped.__cause__ is ccxt_error


def test_retries_transient_errors_with_backoff_then_succeeds() -> None:
    client = FakeCcxt(failures=[ccxt.RequestTimeout("t"), ccxt.RateLimitExceeded("429")])
    exchange, sleeps = make_exchange(client, rate_limit_min_wait_s=5.0)
    assert exchange.fetch_time() == client.server_time_ms
    assert client.count("fetch_time") == 3
    assert sleeps == [1.0, 5.0]  # 2^0 = 1 s; el 429 espera al menos 5 s


def test_gives_up_after_max_retries_with_mapped_error() -> None:
    client = FakeCcxt(failures=[ccxt.ExchangeNotAvailable("503")] * 10)
    exchange, sleeps = make_exchange(client, max_retries=3)
    with pytest.raises(ExchangeUnavailable):
        exchange.fetch_time()
    assert client.count("fetch_time") == 4
    assert sleeps == [1.0, 2.0, 4.0]


def test_rate_limit_exhausted_maps_to_rate_limited() -> None:
    client = FakeCcxt(failures=[ccxt.RateLimitExceeded("429")] * 10)
    exchange, _ = make_exchange(client, max_retries=2)
    with pytest.raises(RateLimited):
        exchange.fetch_time()


@pytest.mark.parametrize(
    ("ccxt_error", "domain_error"),
    [
        (ccxt.InvalidOrder("x"), InvalidOrder),
        (ccxt.InsufficientFunds("x"), InsufficientFunds),
        (ccxt.AuthenticationError("x"), AuthError),
    ],
)
def test_never_retries_non_transient_errors(
    ccxt_error: Exception, domain_error: type[ExchangeError]
) -> None:
    client = FakeCcxt(failures=[ccxt_error])
    exchange, sleeps = make_exchange(client)
    with pytest.raises(domain_error):
        exchange.load_markets()
    assert client.count("load_markets") == 1
    assert sleeps == []


# --------------------------------------------------------------------------- OHLCV


def test_parse_kline_row_keeps_binance_strings_exact() -> None:
    row = [
        T0,
        "27123.45000000",
        "27200.10000000",
        "27000.00000000",
        "27150.55000000",
        "123456789.12345678",
        T0 + H4_MS - 1,
    ]
    candle = parse_kline_row(row, BTC, Timeframe.H4)
    assert candle.open == Decimal("27123.45")
    assert candle.volume == Decimal("123456789.12345678")  # 17 dígitos: un float lo alteraría
    assert candle.open_time == T0
    with pytest.raises(ExchangeError, match="incompleta"):
        parse_kline_row([T0, "1.0"], BTC, Timeframe.H4)
    with pytest.raises(ExchangeError, match="inválida"):
        parse_kline_row([T0, "abc", "1", "1", "1", "1"], BTC, Timeframe.H4)


def test_fetch_ohlcv_paginates_dedupes_and_respects_until() -> None:
    n = 2_500
    client = FakeCcxt(candles={("BTC/USDT", "4h"): ohlcv_rows(T0, H4_MS, n)})
    exchange, _ = make_exchange(client)
    candles = exchange.fetch_ohlcv(BTC, Timeframe.H4, T0)
    assert len(candles) == n
    assert client.count("klines") == 3
    assert [c.open_time for c in candles] == sorted({c.open_time for c in candles})
    # Cada página arranca donde terminó la anterior + 1 vela (sin re-pedir la última).
    sinces = [call[1][2] for call in client.calls if call[0] == "klines"]
    assert sinces == [T0, T0 + 1000 * H4_MS, T0 + 2000 * H4_MS]

    until = T0 + 1_500 * H4_MS
    subset = exchange.fetch_ohlcv(BTC, Timeframe.H4, T0, until)
    assert len(subset) == 1_500
    assert subset[-1].open_time == until - H4_MS


def test_fetch_ohlcv_small_pages_and_empty_ranges() -> None:
    client = FakeCcxt(candles={("BTC/USDT", "4h"): ohlcv_rows(T0, H4_MS, 25)})
    exchange, _ = make_exchange(client)
    assert len(exchange.fetch_ohlcv(BTC, Timeframe.H4, T0, page_limit=10)) == 25
    assert client.count("klines") == 3  # 10 + 10 + 5 (sin until, página incompleta termina)
    assert exchange.fetch_ohlcv(BTC, Timeframe.H4, T0 + 100 * H4_MS) == []
    with pytest.raises(ValueError, match="limit"):
        exchange.fetch_ohlcv_page(BTC, Timeframe.H4, T0, limit=OHLCV_PAGE_LIMIT + 1)


def test_fetch_ohlcv_max_pages_bounds_requests() -> None:
    client = FakeCcxt(candles={("BTC/USDT", "4h"): ohlcv_rows(T0, H4_MS, 50)})
    exchange, _ = make_exchange(client)
    assert len(exchange.fetch_ohlcv(BTC, Timeframe.H4, T0, page_limit=10, max_pages=2)) == 20


# --------------------------------------------------------------------------- reloj


def test_time_offset_is_cached_and_refreshed() -> None:
    local = {"now": 1_000_000}
    client = FakeCcxt(server_time_ms=1_000_000 + 250)
    exchange = BinanceExchange(
        client, local_now_ms=lambda: local["now"], offset_refresh_ms=3_600_000
    )
    assert exchange.time_offset_ms() == 250
    assert exchange.now_ms() == local["now"] + 250
    exchange.now_ms()
    assert client.count("fetch_time") == 1
    local["now"] += 3_600_000
    client.server_time_ms = local["now"] - 100
    assert exchange.time_offset_ms() == -100
    assert client.count("fetch_time") == 2
    exchange.time_offset_ms(force=True)
    assert client.count("fetch_time") == 3


# --------------------------------------------------------------------------- snapshot


def test_packaged_snapshot_covers_the_universe() -> None:
    snapshot = load_markets_snapshot()
    by_pair = snapshot.by_pair()
    for symbol in (
        "BTC/USDT",
        "ETH/USDT",
        "BNB/USDT",
        "XRP/USDT",
        "ADA/USDT",
        "LTC/USDT",
        "LINK/USDT",
        "SOL/USDT",
    ):
        assert Pair.parse(symbol) in by_pair
    btc = by_pair[BTC]
    assert btc.tick_size == Decimal("0.01")
    assert btc.step_size == Decimal("0.00001")
    assert btc.min_notional == Decimal("5")
    assert snapshot.rate_limits.request_weight_per_minute == 6000


def test_snapshot_round_trip(tmp_path: Path) -> None:
    client = FakeCcxt(
        markets={
            "BTC/USDT": binance_market("BTC"),
            "ETH/USDT": binance_market("ETH", step="0.00010000"),
        }
    )
    exchange, _ = make_exchange(client)
    snapshot = build_markets_snapshot(exchange, (BTC, ETH), source="test")
    path = tmp_path / "snap.json"
    save_markets_snapshot(snapshot, path)
    loaded = load_markets_snapshot(path)
    assert loaded == snapshot
    assert loaded.by_pair()[ETH].step_size == Decimal("0.0001")
    assert '"step_size": "0.0001"' in path.read_text(encoding="utf-8")
    with pytest.raises(ExchangeError, match="no listados"):
        build_markets_snapshot(exchange, (Pair.parse("SOL/USDT"),))


# --------------------------------------------------------------------------- revisión Fase 2


def test_ip_ban_418_is_not_retried() -> None:
    ban = ccxt.DDoSProtection(
        "binance GET https://api.binance.com/api/v3/klines?symbol=BTCUSDT 418 I'm a teapot "
        '{"code":-1003,"msg":"Way too much request weight used; IP banned until 1700000000000."}'
    )
    client = FakeCcxt(failures=[ban])
    exchange, sleeps = make_exchange(client)
    with pytest.raises(RateLimited, match="banned"):
        exchange.fetch_time()
    assert client.count("fetch_time") == 1
    assert sleeps == []
    assert is_ip_ban(ban)
    assert not is_ip_ban(ccxt.DDoSProtection("429 Too Many Requests"))


def test_retry_after_header_is_honoured_on_429() -> None:
    client = FakeCcxt(failures=[ccxt.RateLimitExceeded("429")])
    client.last_response_headers = {"Retry-After": "12"}
    exchange, sleeps = make_exchange(client)
    exchange.fetch_time()
    assert sleeps == [12.0]


def test_broken_responses_are_retried_as_operation_failed() -> None:
    client = FakeCcxt(failures=[ccxt.BadResponse("html en vez de json")])
    exchange, sleeps = make_exchange(client)
    assert exchange.fetch_time() == client.server_time_ms
    assert sleeps == [1.0]


@pytest.mark.parametrize("ccxt_error", [ccxt.BadRequest("400"), ccxt.ExchangeError("otro")])
def test_generic_exchange_errors_are_not_retried(ccxt_error: Exception) -> None:
    client = FakeCcxt(failures=[ccxt_error])
    exchange, sleeps = make_exchange(client)
    with pytest.raises(ExchangeError):
        exchange.load_markets()
    assert sleeps == []


def test_redact_strips_query_strings() -> None:
    text = "binance GET https://api.binance.com/api/v3/order?symbol=BTCUSDT&signature=abc 400 x"
    assert "signature" not in redact(text)
    assert redact(text).startswith("binance GET https://api.binance.com/api/v3/order?<query")


def test_short_intermediate_page_does_not_stop_pagination_when_until_is_set() -> None:
    # Hueco de 3 velas entre la 10 y la 13: la primera página (limit 10) vuelve completa, la
    # segunda arranca en la 10 y devuelve solo 2 (desde la 13) → sin `until` cortaría acá.
    rows = ohlcv_rows(T0, H4_MS, 10) + ohlcv_rows(T0 + 13 * H4_MS, H4_MS, 12, base_price=113)
    client = FakeCcxt(candles={("BTC/USDT", "4h"): rows})
    exchange, _ = make_exchange(client)

    # Fake que corta artificialmente la segunda página a 2 velas para simular una página corta.
    original = client.public_get_klines

    def flaky(params: dict[str, object] | None = None) -> list[list[object]]:
        rows_ = original(params)
        if params and params.get("startTime") == T0 + 10 * H4_MS:
            return rows_[:2]
        return rows_

    client.public_get_klines = flaky  # type: ignore[method-assign]
    until = T0 + 25 * H4_MS
    candles = exchange.fetch_ohlcv(BTC, Timeframe.H4, T0, until, page_limit=10)
    assert len(candles) == 22
    assert candles[-1].open_time == until - H4_MS
    assert client.count("klines") == 3  # 10 + 2 (corta, sigue) + 10 (llega a until)


def test_fetch_last_price_reads_exact_string() -> None:
    client = FakeCcxt()
    client.last_prices["BTCUSDT"] = "65000.12345678"
    exchange, _ = make_exchange(client)
    assert exchange.fetch_last_price(BTC) == Decimal("65000.12345678")
    client.last_prices["BTCUSDT"] = "0"
    with pytest.raises(ExchangeError, match="sin precio"):
        exchange.fetch_last_price(BTC)
