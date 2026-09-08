# Fixtures OHLCV

Velas 4h del año 2023 con el esquema del `ParquetStore` (`open_time` int64 ms UTC + OHLCV en `decimal128(24, 8)`).

| Archivo | Origen | Uso |
|---|---|---|
| `synthetic-BTCUSDT-4h-2023.parquet`, `synthetic-ETHUSDT-4h-2023.parquet` | Paseo geométrico con semilla fija (`scripts/gen_ohlcv_fixtures.py`) | Suite unitaria: store, feeds, CLI |
| `BTCUSDT-4h-2023.parquet`, `ETHUSDT-4h-2023.parquet` | Binance real, copiadas desde `data/` con `--from-data` | Fase 3: indicadores vs TA-Lib. **Pendiente**: se generan desde una máquina con acceso a Binance |

Regenerar:

```bash
uv run python scripts/gen_ohlcv_fixtures.py                    # sintéticos
uv run tradingbot download-data -p BTC/USDT,ETH/USDT -t 4h     # 1) bajar datos reales
uv run python scripts/gen_ohlcv_fixtures.py --from-data data   # 2) copiar 2023 a fixtures
```

Ningún test depende de `data/` (gitignored).
