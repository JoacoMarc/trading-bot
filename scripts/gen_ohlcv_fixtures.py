#!/usr/bin/env python3
"""Genera los fixtures parquet de `tests/fixtures/ohlcv/`.

Dos modos:

- `--from-data data` (recomendado, requiere haber corrido `tradingbot download-data`): copia
  las velas 4h de 2023 de BTC/USDT y ETH/USDT desde el store real a
  `tests/fixtures/ohlcv/BTCUSDT-4h-2023.parquet` y `ETHUSDT-4h-2023.parquet`.
- sin argumentos: series **sintéticas** (paseo geométrico con semilla fija) con el mismo esquema
  y rango, guardadas como `synthetic-BTCUSDT-4h-2023.parquet` y `synthetic-ETHUSDT-4h-2023.parquet`.
  Sirven para tests de store/feed/CLI; para indicadores contra TA-Lib (Fase 3) usar las reales.

Uso: `uv run python scripts/gen_ohlcv_fixtures.py [--from-data data] [--out tests/fixtures/ohlcv]`
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np

from tradingbot.data.store import ParquetStore, candles_to_frame, write_parquet
from tradingbot.domain.candle import Candle
from tradingbot.domain.pair import Pair
from tradingbot.domain.timeframe import Timeframe

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "tests" / "fixtures" / "ohlcv"
YEAR_START_MS = int(datetime(2023, 1, 1, tzinfo=UTC).timestamp() * 1000)
YEAR_END_MS = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)
TIMEFRAME = Timeframe.H4
SPECS: dict[str, tuple[float, float, int]] = {
    # base: (precio inicial, volatilidad por vela, semilla)
    "BTC": (16_500.0, 0.012, 20230101),
    "ETH": (1_200.0, 0.015, 20230102),
}
TICK = Decimal("0.01")
VOL_STEP = Decimal("0.00001")


def _q(value: float, step: Decimal) -> Decimal:
    return Decimal(repr(value)).quantize(step, rounding=ROUND_HALF_UP)


def synthetic_candles(pair: Pair, start_price: float, vol: float, seed: int) -> list[Candle]:
    """Paseo geométrico con drift leve; OHLC coherentes; volumen lognormal."""
    rng = np.random.default_rng(seed)
    n = (YEAR_END_MS - YEAR_START_MS) // TIMEFRAME.ms
    returns = rng.normal(loc=0.0002, scale=vol, size=n)
    closes = start_price * np.exp(np.cumsum(returns))
    opens = np.concatenate(([start_price], closes[:-1]))
    wick_up = np.abs(rng.normal(0, vol / 2, size=n))
    wick_down = np.abs(rng.normal(0, vol / 2, size=n))
    highs = np.maximum(opens, closes) * (1 + wick_up)
    lows = np.minimum(opens, closes) * (1 - wick_down)
    volumes = rng.lognormal(mean=np.log(2_000.0), sigma=0.6, size=n)
    candles: list[Candle] = []
    for i in range(n):
        o, h, l_, c = (_q(float(x), TICK) for x in (opens[i], highs[i], lows[i], closes[i]))
        h = max(h, o, c)
        l_ = min(l_, o, c)
        candles.append(
            Candle(
                pair=pair,
                timeframe=TIMEFRAME,
                open_time=YEAR_START_MS + i * TIMEFRAME.ms,
                open=o,
                high=h,
                low=l_,
                close=c,
                volume=_q(float(volumes[i]), VOL_STEP),
            )
        )
    return candles


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-data", type=Path, default=None, help="store real (data/)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    for base, (price, vol, seed) in SPECS.items():
        pair = Pair(base=base, quote="USDT")
        if args.from_data is not None:
            store = ParquetStore(args.from_data)
            frame = store.read(pair, TIMEFRAME, YEAR_START_MS, YEAR_END_MS)
            if frame.empty:
                print(f"{pair}: sin datos 4h de 2023 en {args.from_data}; correr download-data")
                return 1
            target = args.out / f"{pair.binance_symbol}-4h-2023.parquet"
        else:
            frame = candles_to_frame(synthetic_candles(pair, price, vol, seed))
            target = args.out / f"synthetic-{pair.binance_symbol}-4h-2023.parquet"
        rows = write_parquet(target, frame, pair, TIMEFRAME)
        print(f"{target.relative_to(ROOT)}: {rows} velas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
