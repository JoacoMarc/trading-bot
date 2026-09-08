"""Genera los fixtures de referencia de indicadores con TA-Lib.

Lee un parquet del `ParquetStore` (por defecto el fixture real `BTCUSDT-4h-2023`), convierte
OHLCV a float64 y calcula con TA-Lib los indicadores que `tradingbot.indicators` debe reproducir.
Guarda un parquet con las entradas y las salidas (NaN durante el warmup) más un JSON con la
versión de TA-Lib y los parámetros. Requiere el grupo `fixtures`: `uv sync --group fixtures`.

Uso: `uv run python scripts/gen_indicator_fixtures.py [--source ...] [--out-dir ...]`
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import talib

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "tests" / "fixtures" / "ohlcv" / "BTCUSDT-4h-2023.parquet"
DEFAULT_OUT_DIR = ROOT / "tests" / "fixtures" / "indicators"

PARAMS: dict[str, dict[str, int | float]] = {
    "sma_20": {"timeperiod": 20},
    "ema_20": {"timeperiod": 20},
    "ema_50": {"timeperiod": 50},
    "ema_200": {"timeperiod": 200},
    "rsi_14": {"timeperiod": 14},
    "macd_12_26_9": {"fastperiod": 12, "slowperiod": 26, "signalperiod": 9},
    "atr_14": {"timeperiod": 14},
    "adx_14": {"timeperiod": 14},
    "bbands_20_2": {"timeperiod": 20, "nbdevup": 2.0, "nbdevdn": 2.0},
    "max_20": {"timeperiod": 20},
    "min_20": {"timeperiod": 20},
}


def load_ohlcv(path: Path) -> dict[str, np.ndarray]:
    table = pq.read_table(path)
    out: dict[str, np.ndarray] = {"open_time": table.column("open_time").to_numpy()}
    for name in ("open", "high", "low", "close", "volume"):
        out[name] = pc.cast(table.column(name), pa.float64()).to_numpy(zero_copy_only=False)
    return out


def compute(ohlcv: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    close, high, low = ohlcv["close"], ohlcv["high"], ohlcv["low"]
    macd, macd_signal, macd_hist = talib.MACD(close, **PARAMS["macd_12_26_9"])
    upper, middle, lower = talib.BBANDS(close, matype=0, **PARAMS["bbands_20_2"])
    return {
        "sma_20": talib.SMA(close, **PARAMS["sma_20"]),
        "ema_20": talib.EMA(close, **PARAMS["ema_20"]),
        "ema_50": talib.EMA(close, **PARAMS["ema_50"]),
        "ema_200": talib.EMA(close, **PARAMS["ema_200"]),
        "rsi_14": talib.RSI(close, **PARAMS["rsi_14"]),
        "macd_12_26_9": macd,
        "macd_signal_12_26_9": macd_signal,
        "macd_hist_12_26_9": macd_hist,
        "atr_14": talib.ATR(high, low, close, **PARAMS["atr_14"]),
        "adx_14": talib.ADX(high, low, close, **PARAMS["adx_14"]),
        "bb_upper_20_2": upper,
        "bb_middle_20_2": middle,
        "bb_lower_20_2": lower,
        "max_20": talib.MAX(close, **PARAMS["max_20"]),
        "min_20": talib.MIN(close, **PARAMS["min_20"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    source = args.source.resolve()
    ohlcv = load_ohlcv(source)
    outputs = compute(ohlcv)
    stem = f"talib-{source.stem}"
    source_label = (
        source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else str(source)
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)

    columns = {**ohlcv, **outputs}
    table = pa.table({name: pa.array(values) for name, values in columns.items()})
    out_path = args.out_dir / f"{stem}.parquet"
    pq.write_table(table, out_path, compression="zstd")

    meta = {
        "talib_version": talib.__version__,
        "source": source_label,
        "rows": len(ohlcv["open_time"]),
        "compatibility": "TA-Lib default (EMA sembrada con SMA, Wilder en RSI/ATR/ADX)",
        "params": PARAMS,
        "columns": list(columns),
    }
    (args.out_dir / f"{stem}.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"{out_path}: {meta['rows']} filas, {len(outputs)} series de TA-Lib {talib.__version__}")


if __name__ == "__main__":
    main()
