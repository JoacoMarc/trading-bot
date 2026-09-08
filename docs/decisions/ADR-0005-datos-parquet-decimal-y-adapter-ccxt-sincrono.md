# ADR-0005: Velas en parquet `decimal128`, registro de huecos versionado y adapter ccxt síncrono

- Estado: aceptado
- Fecha: 2026-09-08
- Fase: 2

## Contexto

La Fase 2 necesita guardar ~600k velas (8 pares × 1h + 4h desde 2019) y servirlas al backtest sin violar ADR-0003 (dinero en `Decimal`, `float64` solo en `indicators/`). Binance devuelve precios y cantidades como strings con hasta 8 decimales; ccxt los convierte a `float` en `fetch_ohlcv` y en `precision`/`limits`. Además, los huecos reales de Binance (mantenimientos) deben poder distinguirse de datos corruptos, y el plan original los ubicaba en `data/binance/gaps.json`, un directorio gitignored.

## Decisión

1. **Esquema parquet**: `open_time` int64 (ms UTC) + `open/high/low/close/volume` en `decimal128(24, 8)`, un archivo por `data/<exchange>/<BASEQUOTE>/<timeframe>.parquet`, comprimido con zstd y con metadatos `tradingbot.*` (versión, exchange, par, timeframe). La lectura entrega `Decimal` exactos; la conversión a `float64` para indicadores es responsabilidad de `indicators/` (Fase 3).
2. **Frontera con ccxt sin float**: los filtros del mercado (`tickSize`, `stepSize`, `minQty`, `minNotional`) se leen como string desde `market["info"]["filters"]`; las velas se piden con el endpoint crudo `GET /api/v3/klines` (`public_get_klines` de ccxt, con su rate limiter) y no con `fetch_ohlcv`, porque ccxt convierte a `float` y un volumen de 17 dígitos significativos (XRP/ADA en 4h) perdería el último dígito. `to_decimal` recibe strings.
   El corte a velas cerradas usa el reloj del exchange **menos un margen de seguridad** (`close_safety_ms`, 2 s por defecto) que absorbe el error del offset cacheado y el retardo con que Binance publica la vela cerrada; sin él, correr justo después del cierre podía guardar una vela parcial que el live vería distinta (paridad rota).
3. **Registro de huecos versionado** en `configs/binance_gaps.json` (no en `data/`): `data-check` solo alerta por huecos no cubiertos por el registro; `--register` re-pide cada hueco al exchange, guarda lo que exista y registra solo los que vuelven vacíos. La serie guardada se mantiene **contigua**: un `since` posterior a la última vela guardada continúa desde ella, la paginación con `until` no se corta por una página corta, y el progreso se persiste cada 10 páginas, así un hueco en el store nunca es autoinfligido.
4. **Adapter ccxt síncrono** (`exchange/binance.py`) con cliente inyectable (`CcxtClient` Protocol). Reintenta solo `ccxt.OperationFailed` (timeouts, 429, mantenimiento, exchange caído, respuestas rotas) con backoff exponencial, espera mínima ante rate limit y respeto del `Retry-After`; nunca `InvalidOrder`, `InsufficientFunds`, `AuthenticationError` ni un **418** (IP baneada: reintentar alarga el ban). Los mensajes de error se loguean sin query string (en endpoints firmados lleva `signature=`). El reloj del exchange se expone con offset cacheado una hora.
5. **Snapshot de mercados empaquetado** (`exchange/markets_snapshot.json`) para tests y backtests sin red; `download-data` guarda además una copia viva en `data/binance/markets.json`.

## Alternativas consideradas

- **OHLCV en `float64` en parquet**: es lo habitual y más rápido, pero obliga a un `Decimal(str(x))` en cada lectura y a confiar en que el round-trip no cambie ningún valor; con `decimal128` la exactitud es estructural.
- **Strings en parquet**: exactas pero pesadas y sin pushdown de filtros aritméticos.
- **`fetch_ohlcv(params={"paginate": True})` de ccxt**: cómodo, pero el retry por página y el corte en `until` quedan dentro de ccxt; paginamos a mano para controlar reintentos, deduplicación y el límite de velas cerradas.
- **`ccxt.async_support` desde ya**: el `Engine` es async (ADR-0002), pero el downloader es una herramienta de CLI y la Fase 7 puede envolver el cliente síncrono con `asyncio.to_thread` o migrar el `CcxtClient` a la variante async sin tocar la lógica del adapter.
- **Huecos en `data/binance/gaps.json`**: fuera del control de versiones, cada máquina tendría su lista; el registro es conocimiento del proyecto, va en `configs/`.

## Consecuencias

- Los datos guardados son exactamente los que devolvió el exchange; los tests de store usan `hypothesis` sobre valores de 8 decimales.
- Leer un parquet entero a `Decimal` cuesta más que a `float64` (objetos Python); es aceptable para 4h/1h y el backtest lo hace una vez por corrida. Si en Fase 4 pesa, la lectura para indicadores puede pedir `float64` directo a pyarrow sin cambiar el esquema.
- La regla "la vela en formación nunca se guarda" se implementa pidiendo `until = floor(hora_del_exchange)` y verificando de nuevo al recibir; el downloader re-pide la última vela guardada inclusive y hace upsert.
- `decimal128(24, 8)` admite hasta 10¹⁶ en la parte entera: sobra para el universo v1, pero excluiría tokens con volúmenes tipo SHIB/PEPE; cambiar la escala sería una migración del esquema (`schema_version`).
- `HistoricalFeed` toma las `warmup` velas más recientes antes de `start` aunque haya huecos reales en la ventana (lee sin cota inferior); `InsufficientWarmup` solo cuando de verdad no hay velas.
- Deuda: `HistoricalFeed` exige el warmup completo para **todos** los pares; un par listado después del inicio del backtest (SOL en 2019) falla. La Fase 4 decide si el `Engine` habilita pares a medida que cumplen su warmup. Dos `download-data` simultáneos sobre el mismo archivo se pisan (último escritor gana): un lock file en `data/binance/` lo haría explícito. `Gap.covers` no reconoce un hueco cubierto por dos registros adyacentes (falso positivo inofensivo).
